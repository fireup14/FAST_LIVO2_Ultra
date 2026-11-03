#!/usr/bin/env python3
"""Isolated synthetic ROS 2 regressions. Never starts a driver or touches project maps."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import yaml

os.environ.setdefault("ROS_DOMAIN_ID", "179")
os.environ.setdefault("ROS_AUTOMATIC_DISCOVERY_RANGE", "LOCALHOST")
os.environ.setdefault("ROS_LOG_DIR", "/tmp/ultra-regression-ros-logs")
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseWithCovarianceStamped
from std_msgs.msg import Bool
from livox_ros_driver2.msg import CustomMsg, CustomPoint
from fast_livo.msg import State6Stamped
from tf2_msgs.msg import TFMessage


class Runner:
    def __init__(self, install, temporary):
        self.install, self.temporary = install, temporary
        self.node = rclpy.create_node("ultra_regression_observer")
        self.processes = []
        self.results = []
        self.qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                              durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.imu = self.node.create_publisher(Imu, "/livox/imu", 10)
        self.lidar = self.node.create_publisher(CustomMsg, "/livox/lidar", 10)
        self.pose = self.node.create_publisher(PoseWithCovarianceStamped, "/icp_result", self.qos)
        self.cloud_points = []
        self.acceleration=(0.,0.,9.81)
        for a in range(20):
            for b in range(20):
                self.cloud_points.extend([(1.01+a*.02,1.01+b*.02,1.),
                                          (1.,1.01+a*.02,1.01+b*.02),
                                          (1.01+a*.02,1.,1.01+b*.02)])
        self.map = self.temporary / "prior.pcd"
        self.write_map(self.map, self.cloud_points)
        self.sparse = self.temporary / "sparse.pcd"
        self.write_map(self.sparse, [(1+2*i,1,1) for i in range(20)])

    def check(self, condition, label):
        if not condition:
            raise AssertionError(label)
        self.results.append(label)
        print("PASS", label, flush=True)

    def write_map(self, file, points):
        file.write_text("VERSION .7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\nWIDTH " + str(len(points)) +
                        "\nHEIGHT 1\nPOINTS " + str(len(points)) + "\nDATA ascii\n" +
                        "\n".join(" ".join(map(str, p)) for p in points)+"\n")

    def start(self, package, executable, parameters):
        config=self.temporary/f"params-{len(self.processes)}.yaml"
        config.write_text(yaml.safe_dump({"/**":{"ros__parameters":parameters}}))
        log=self.temporary/f"process-{len(self.processes)}.log"
        stream=log.open("w")
        process=subprocess.Popen([str(self.install/package/"lib"/package/executable),"--ros-args","--params-file",str(config)],
                                 stdout=stream,stderr=subprocess.STDOUT)
        self.processes.append((process,stream,log))
        return process,log

    def stop(self, process):
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try: process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()

    def spin(self, seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            rclpy.spin_once(self.node,timeout_sec=.01)

    def base(self):
        return {"time_check.enabled":False,"common.img_en":0,"pcd_save.pcd_save_en":False,
                "extrin_calib.extrinsic_R":[1.,0.,0.,0.,1.,0.,0.,0.,1.],
                "extrin_calib.extrinsic_T":[0.,0.,0.],"imu.imu_int_frame":2,
                "preprocess.point_filter_num":1,"preprocess.blind":.1,
                "preprocess.filter_size_surf":.02,"publish.pub_plane_en":False}

    def feed(self, seconds, shift=0.):
        end=time.monotonic()+seconds
        next_scan=0
        while time.monotonic()<end:
            now=self.node.get_clock().now()
            imu=Imu(); imu.header.stamp=now.to_msg()
            imu.linear_acceleration.x,imu.linear_acceleration.y,imu.linear_acceleration.z=self.acceleration
            self.imu.publish(imu)
            if time.monotonic()>=next_scan:
                cloud=CustomMsg(); cloud.header.stamp=rclpy.time.Time(nanoseconds=now.nanoseconds-100_000_000).to_msg()
                cloud.header.frame_id="livox_frame"
                for i,(x,y,z) in enumerate(self.cloud_points):
                    p=CustomPoint();p.x=x+shift;p.y=y;p.z=z;p.tag=0x10;p.line=0;p.reflectivity=100
                    p.offset_time=int(i*99_000_000/max(1,len(self.cloud_points)-1));cloud.points.append(p)
                cloud.point_num=len(cloud.points);self.lidar.publish(cloud)
                next_scan=time.monotonic()+.1
            rclpy.spin_once(self.node,timeout_sec=.002)
            time.sleep(.003)

    def mapping(self, prior=False, sparse=False, gravity=False):
        self.node.destroy_publisher(self.pose)
        self.pose=self.node.create_publisher(PoseWithCovarianceStamped,"/icp_result",self.qos)
        parameters=self.base()
        parameters["uav.gravity_align_en"]=gravity
        self.acceleration=(2.,0.,(9.81**2-4)**.5) if gravity else (0.,0.,9.81)
        parameters.update({"locate_in_prior_map":prior,"prior_map_path":str(self.sparse if sparse else self.map)})
        odom=[];final=[];state=[];valid=[]
        subscriptions=[self.node.create_subscription(Odometry,"/aft_mapped_to_init",odom.append,10),
                       self.node.create_subscription(PoseWithCovarianceStamped,"/fast_livo2/initial_map_pose",final.append,self.qos),
                       self.node.create_subscription(State6Stamped,"/fast_livo2/state6_stamped",state.append,10),
                       self.node.create_subscription(Bool,"/fast_livo2/tracking_valid",valid.append,self.qos)]
        process,log=self.start("fast_livo","fastlivo_mapping",parameters)
        try:
            self.spin(.6)
            if prior:
                self.check(process.poll() is None,"prior waits without exiting")
                info=self.node.get_subscriptions_info_by_topic("/livox/imu")
                self.check(not any(x.node_name=="laserMapping" for x in info),"no IMU subscription before initial pose")
                pose=PoseWithCovarianceStamped();pose.header.frame_id="map";pose.pose.pose.orientation.w=1.
                self.pose.publish(pose);self.spin(.3)
            self.feed(2.)
            if sparse:
                self.spin(.2)
                self.check(process.poll()==1 and not final,"zero-plane prior exits without final pose")
                self.check("zero valid planes" in log.read_text(),"zero-plane failure explains filter remediation")
            else:
                self.check(process.poll() is None,"synthetic LIO remains alive")
                self.check(len(odom)>2 and len(state)>2,"synthetic LIO publishes pose and stamped state")
                self.check(state[-1].valid and state[-1].header.frame_id=="aft_mapped","stamped state carries validity and frame")
                gravity=state[-1].projected_gravity
                self.check(abs(gravity.x**2+gravity.y**2+gravity.z**2-1)<1e-5,"stamped state unit gravity convention")
                if prior:
                    self.check(len(final)==1,"prior publishes exactly one final alignment")
                    self.feed(1.,shift=100.)
                    self.spin(.1)
                    self.check(process.poll()==1 and valid and not valid[-1].data,"constraint loss marks invalid and stops localization")
        finally:
            self.stop(process)
            if not sparse and not prior:
                self.check(process.returncode==0,"ordinary LIO SIGINT exits cleanly")
            for sub in subscriptions:self.node.destroy_subscription(sub)

    def failures(self):
        cases=[({"preprocess.filter_size_surf":0.},"invalid surface filter"),
               ({"pcd_save.interval":0},"zero save interval"),
               ({"extrin_calib.extrinsic_T":[0.]},"short IMU extrinsics"),
               ({"locate_in_prior_map":True,"prior_map_path":"/missing/map.pcd"},"missing prior map")]
        for overrides,label in cases:
            parameters=self.base();parameters.update(overrides)
            process,log=self.start("fast_livo","fastlivo_mapping",parameters)
            process.wait(timeout=5)
            self.check(process.returncode==1,label+" exits with code 1")

    def registration(self):
        for executable in ["icp_node","small_gicp_node","teaser_node","sac_ia_gicp","teaser_gicp_node"]:
            process,log=self.start("relocalization",executable,{"locate_in_prior_map":False})
            self.spin(.25); self.check(process.poll() is None,executable+" disabled mode stays lightweight/alive")
            self.stop(process);self.check(process.returncode==0,executable+" SIGINT exits cleanly")
        parameters={"locate_in_prior_map":True,"prior_map_path":str(self.map),
                    "extrin_calib.extrinsic_R":[1.,0.,0.,0.,1.,0.,0.,0.,1.],
                    "extrin_calib.extrinsic_T":[.1,0.,0.],"algorithm":"icp","num_threads":2,
                    "map_voxel_leaf_size":.04,"gicp_map_voxel_leaf_size":.04,
                    "gicp_cloud_voxel_leaf_size":.04,"converged_count_thre":2,"gicp_solver_max_iter":20,
                    "result_hold_seconds":2.,"timeout_seconds":5.}
        process,log=self.start("relocalization","teaser_gicp_node",parameters)
        self.spin(.5);self.feed(.7)
        received=[]
        sub=self.node.create_subscription(PoseWithCovarianceStamped,"/icp_result",received.append,self.qos)
        self.spin(.3)
        self.check(any(abs(m.pose.pose.position.x+.1)<.02 for m in received),"ICP success converts LiDAR pose to IMU and retains result for late subscriber")
        self.node.destroy_subscription(sub)
        self.stop(process)
        parameters["timeout_seconds"]=.2
        process,log=self.start("relocalization","teaser_gicp_node",parameters)
        process.wait(timeout=5)
        self.check(process.returncode==1 and "timed out" in log.read_text(),"registration timeout returns code 1")

    def visual_start(self):
        parameters=self.base()
        parameters.update({"common.img_en":1,"camera.model":"Pinhole","camera.width":640,"camera.height":360,
                           "camera.fx":328.,"camera.fy":327.,"camera.cx":319.,"camera.cy":179.,
                           "extrin_calib.T_cl":[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.],
                           "vio.img_point_cov":1000.5,"vio.outlier_threshold":999.5})
        process,log=self.start("fast_livo","fastlivo_mapping",parameters)
        self.spin(.5)
        self.check(process.poll() is None,"visual startup accepts T_cl and fractional noise")
        self.check(any(x.node_name=="laserMapping" for x in self.node.get_subscriptions_info_by_topic("/left_camera/image")),"visual startup creates image subscription")
        self.stop(process)
        self.check(process.returncode==0,"visual startup SIGINT exits cleanly")

    def final_tf(self):
        received=[]
        subscription=self.node.create_subscription(TFMessage,"/tf_static",received.append,self.qos)
        publisher=self.node.create_publisher(PoseWithCovarianceStamped,"/fast_livo2/initial_map_pose",self.qos)
        process,log=self.start("relocalization","transform_publisher",{
            "initial_pose_topic":"/fast_livo2/initial_map_pose","initial_pose_transient_local":True})
        self.spin(.3)
        self.check(not received,"TF does not publish before final mapping alignment")
        pose=PoseWithCovarianceStamped();pose.header.frame_id="wrong";pose.pose.pose.orientation.w=2.
        publisher.publish(pose);self.spin(.2)
        self.check(not received,"TF rejects invalid alignment frame")
        pose.header.frame_id="map";pose.pose.pose.position.x=3.
        publisher.publish(pose);self.spin(.2)
        self.check(received and received[-1].transforms[0].transform.translation.x==3. and received[-1].transforms[0].transform.rotation.w==1.,"TF uses final alignment and normalizes quaternion")
        before=len(received);pose.pose.pose.position.x=9.;publisher.publish(pose);self.spin(.2)
        self.check(len(received)==before,"TF freezes the first valid alignment")
        self.stop(process);self.node.destroy_subscription(subscription);self.node.destroy_publisher(publisher)

    def shutdown_stress(self, repetitions):
        for index in range(repetitions):
            process,log=self.start("fast_livo","fastlivo_mapping",self.base())
            deadline=time.monotonic()+3.
            while "PCD 保存已关闭" not in log.read_text() and time.monotonic()<deadline and process.poll() is None:
                self.spin(.01)
            self.spin(.03+(index%5)*.007)
            self.stop(process)
            self.check(process.returncode==0,f"SIGINT wait-set race stress {index+1}/{repetitions}")

    def close(self):
        for process,stream,log in self.processes:self.stop(process);stream.close()
        self.node.destroy_node()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install",type=Path,required=True)
    parser.add_argument("--shutdown-repeats",type=int,default=0)
    args=parser.parse_args()
    rclpy.init()
    with tempfile.TemporaryDirectory(prefix="ultra-ros-regression-") as directory:
        runner=Runner(args.install,Path(directory))
        try:
            runner.failures();runner.mapping();runner.mapping(prior=True)
            runner.mapping(gravity=True);runner.mapping(prior=True,gravity=True)
            runner.mapping(prior=True,sparse=True);runner.registration();runner.visual_start();runner.final_tf()
            runner.shutdown_stress(args.shutdown_repeats)
            report={"passed":len(runner.results),"checks":runner.results}
            (Path(os.environ.get("ULTRA_TEST_REPORT","/tmp/ultra-ros-test-report.json"))).write_text(json.dumps(report,ensure_ascii=False,indent=2))
            print("PASS",len(runner.results),"ROS integration checks")
        except Exception:
            for _,_,log in runner.processes:
                print("LOG",log,"\n",log.read_text()[-6000:],flush=True)
            raise
        finally:runner.close();rclpy.shutdown()

if __name__=="__main__":main()
