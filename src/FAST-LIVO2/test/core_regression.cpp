#include "LIVMapper.h"
#include <filesystem>
#include <stdexcept>
#include <unistd.h>

static void check(bool condition, const char *message) {
  if (!condition) throw std::runtime_error(message);
}

template<class F> static void rejects(F f, const char *message) {
  bool rejected=false;
  try { f(); } catch(const std::exception &) { rejected=true; }
  check(rejected,message);
}

int main(int argc, char **argv) {
  rclcpp::init(argc,argv);
  int count=0;
  try {
    rclcpp::NodeOptions options;
    options.automatically_declare_parameters_from_overrides(true);
    options.parameter_overrides({
      {"time_check.enabled",false}, {"common.img_en",0},
      {"time_offset.imu_time_offset",0.03}, {"imu.b_acc_cov",0.002}, {"imu.b_gyr_cov",0.003},
      {"vio.img_point_cov",123.5}, {"vio.outlier_threshold",234.5},
      {"extrin_calib.extrinsic_R",std::vector<double>{1,0,0,0,1,0,0,0,1}},
      {"extrin_calib.extrinsic_T",std::vector<double>{0,0,0}}
    });
    rclcpp::Node::SharedPtr node;
    LIVMapper mapper(node,"core_regression",options);
    check(mapper.vio_manager->cam==nullptr,"LIO initialized a camera"); ++count;
    mapper.initializeSubscribersAndPublishers(node);
    check(!mapper.sub_img,"LIO created an image subscription"); ++count;
    check(mapper.b_acc_cov==0.002 && mapper.b_gyr_cov==0.003,"Bias parameters were ignored"); ++count;
    check(mapper.p_imu->cov_bias_acc.isApprox(V3D::Constant(0.002)) && mapper.p_imu->cov_bias_gyr.isApprox(V3D::Constant(0.003)),"Bias noise did not reach IMU processor"); ++count;
    check(mapper.IMG_POINT_COV==123.5 && mapper.outlier_threshold==234.5,"Fractional visual noise lost precision"); ++count;
    check(mapper.filter_size_map_min==0.1,"Unsafe prior filter fallback"); ++count;
    mapper.last_timestamp_lidar=100.0;
    mapper.last_timestamp_imu=99.0;
    auto imu=std::make_shared<sensor_msgs::msg::Imu>();
    imu->header.stamp=sec2Stamp(100.03);
    imu->linear_acceleration.z=9.81;
    mapper.imu_cbk(imu);
    check(std::abs(mapper.last_timestamp_imu-100.0)<1e-8 && mapper.imu_buffer.size()==1,"IMU jump/offset did not recover"); ++count;
    imu->header.stamp=sec2Stamp(100.04); mapper.imu_cbk(imu);
    check(mapper.imu_buffer.size()==2,"IMU remained locked after jump"); ++count;

    mapper.locate_in_prior_map=true;
    mapper.initial_pose_received=true;
    mapper.gravity_align_en=true;
    mapper.gravity_align_finished=true;
    mapper.p_imu->imu_need_init=false;
    const M3D A=Eigen::AngleAxisd(0.3,V3D::UnitX()).toRotationMatrix();
    mapper.gravity_alignment_rotation_=A;
    mapper.initial_pose.pose.pose.position.x=2;
    mapper.initial_pose.pose.pose.orientation.w=1;
    check(mapper.prepareInitialMapPose(),"Gravity alignment preparation failed");
    check((mapper.initial_map_transform_.block<3,3>(0,0)-A.transpose()).norm()<1e-9,"Wrong gravity compensation inverse"); ++count;

    auto &manager=*mapper.voxelmap_manager;
    manager.feats_down_world_->clear();
    for(int i=0;i<12;++i) { PointType p{}; p.x=2*i+1; p.y=1; p.z=1; manager.feats_down_world_->push_back(p); }
    *manager.feats_down_body_=*manager.feats_down_world_;
    rejects([&]{mapper.initializeVoxelMap();},"Zero-plane prior was accepted");
    check(!mapper.lidar_map_inited,"Failed prior marked initialized"); ++count;
    for(auto &entry:manager.voxel_map_) delete entry.second;
    manager.voxel_map_.clear();
    manager.feats_down_world_->clear();
    for(int x=0;x<20;++x) for(int y=0;y<20;++y) {
      PointType p{}; p.x=1.01+x*0.02; p.y=1.01+y*0.02; p.z=1.0; manager.feats_down_world_->push_back(p);
    }
    *manager.feats_down_body_=*manager.feats_down_world_;
    mapper.initializeVoxelMap();
    check(manager.countValidPlanes()>0 && mapper.lidar_map_inited,"Dense planar prior rejected"); ++count;
    manager.feats_down_size_=manager.feats_down_body_->size();
    *manager.feats_undistort_=*manager.feats_down_body_;
    StatesGroup predicted;
    manager.state_=predicted;
    check(manager.StateEstimation(predicted),"Planar self-match failed"); ++count;
    for(auto &p:*manager.feats_down_body_) p.x+=100;
    manager.state_=predicted;
    check(!manager.StateEstimation(predicted) && manager.state_.cov.allFinite(),"Zero-constraint state was accepted"); ++count;

    auto &vio=*mapper.vio_manager;
    rejects([&]{vio.setLidarToCameraExtrinsic(std::vector<double>{1},std::vector<double>{0});},"Short camera extrinsics accepted"); ++count;
    std::vector<double> camera{1,0,0,0.1,0,1,0,0.2,0,0,1,0.3,0,0,0,1};
    vio.setLidarToCameraExtrinsic(camera);
    check(std::abs(vio.Pcl.x()-0.1)<1e-9,"T_cl translation wrong"); ++count;
    camera[15]=2; rejects([&]{vio.setLidarToCameraExtrinsic(camera);},"Invalid homogeneous row accepted"); ++count;
    cv::Mat empty; std::vector<pointWithVar> pv;
    vio.processFrame(empty,pv,mapper.voxel_map,0); ++count;

    mapper._state=StatesGroup();
    mapper._state.pos_end=V3D(1,0,0);
    mapper._state.vel_end=V3D(1,2,3);
    mapper._state.cov.setIdentity(); mapper._state.cov(3,3)=2; mapper._state.cov(4,4)=3;
    mapper.geoQuat.w=1; mapper.geoQuat.x=mapper.geoQuat.y=mapper.geoQuat.z=0;
    mapper.LidarMeasures.last_lio_update_time=100.0;
    geometry_msgs::msg::TransformStamped tf;
    tf.header.frame_id="map"; tf.child_frame_id="camera_init";
    tf.transform.rotation.z=std::sqrt(0.5); tf.transform.rotation.w=std::sqrt(0.5);
    mapper.tf_buffer_->setTransform(tf,"regression",true);
    mapper.publish_odometry(mapper.pubOdomAftMapped);
    check(std::abs(mapper.odomAftMappedInMap.pose.pose.position.y-1)<1e-8,"Global pose transform wrong"); ++count;
    check(std::abs(mapper.odomAftMappedInMap.pose.covariance[0]-3)<1e-8,"Global covariance not rotated"); ++count;
    check(std::abs(mapper.odomAftMappedInMap.twist.twist.linear.x-1)<1e-8,"Body twist rotated twice"); ++count;
    check(mapper.odomAftMappedInMap.twist.covariance[0]>0,"Twist covariance not populated"); ++count;

    const auto output=std::filesystem::temp_directory_path()/("ultra-core-"+std::to_string(getpid()));
    std::filesystem::create_directories(output);
    mapper.pcd_output_dir=output.string(); mapper.pcd_file_prefix="test";
    mapper.pcd_save_en=true; mapper.pcd_save_in_localization=false;
    PointType p{};p.x=1;p.y=2;p.z=3;p.intensity=4;
    mapper.pcl_wait_save_intensity->push_back(p);
    mapper.savePCD();
    check(std::filesystem::is_empty(output),"Disabled localization wrote output"); ++count;
    mapper.pcd_save_in_localization=true; mapper.pcd_save_interval=10;
    mapper.savePCD();
    PointCloudXYZI saved;
    check(pcl::io::loadPCDFile((output/"test_remainder.pcd").string(),saved)==0 && saved.size()==1,"Partial final segment lost"); ++count;
    check(std::filesystem::exists(output/"test_metadata.yaml"),"Session transform metadata missing"); ++count;
    for (int coordinate=0;coordinate<3;++coordinate) {
      mapper.pcl_wait_save_intensity->clear();
      mapper.pcd_file_prefix="coordinate"+std::to_string(coordinate);
      mapper.pcd_save_type=coordinate; mapper.pcd_save_interval=-1;
      mapper.initial_map_transform_.setIdentity(); mapper.initial_map_transform_(0,3)=2;
      mapper.pcl_w_wait_pub->push_back(p);
      mapper.feats_undistort->clear(); mapper.feats_undistort->push_back(p);
      mapper.publish_frame_world(mapper.pubLaserCloudFullRes,mapper.vio_manager);
      mapper.savePCD(); saved.clear();
      pcl::io::loadPCDFile((output/(mapper.pcd_file_prefix+".pcd")).string(),saved);
      check(saved.size()==1 && std::abs(saved[0].x-(coordinate==2?3:1))<1e-6,"PCD coordinate selection incorrect"); ++count;
    }
    std::filesystem::remove_all(output);
    rclcpp::shutdown();
    std::cout << "PASS " << count << " core regression checks" << std::endl;
  } catch(const std::exception &error) {
    rclcpp::shutdown();
    std::cerr << "FAIL: " << error.what() << std::endl;
    return 1;
  }
  return 0;
}
