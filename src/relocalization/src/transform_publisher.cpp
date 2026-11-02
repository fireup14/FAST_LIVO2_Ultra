/*
将配置的话题中的最终局部参考系位姿直接发布为静态 TF。
开启重力对齐的定位模式使用建图完成初始化后发布的最终位姿。
*/
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/pose_with_covariance_stamped.hpp>
#include <tf2_ros/static_transform_broadcaster.h>
#include <tf2/LinearMath/Quaternion.h>

class TransformPublisherNode : public rclcpp::Node
{
public:
    TransformPublisherNode()
        : Node("transform_publisher_node")
    {
        this->declare_parameter<std::string>("odom_frame_id","camera_init");
        this->declare_parameter<std::string>("map_frame_id","map");
        this->declare_parameter<std::string>("initial_pose_topic", "icp_result");
        this->declare_parameter<bool>("initial_pose_transient_local", false);

        this->get_parameter_or<std::string>("odom_frame_id", odom_frame_id, "camera_init");
        this->get_parameter_or<std::string>("map_frame_id", map_frame_id, "map");
        const auto topic = this->get_parameter("initial_pose_topic").as_string();
        const bool transient_local = this->get_parameter("initial_pose_transient_local").as_bool();
        auto qos = rclcpp::QoS(transient_local ? 1 : 10).reliable();
        if (transient_local) qos.transient_local();
        broadcaster_ = std::make_shared<tf2_ros::StaticTransformBroadcaster>(this);
        subscription_ = this->create_subscription<geometry_msgs::msg::PoseWithCovarianceStamped>(
            topic, qos, std::bind(&TransformPublisherNode::callback, this, std::placeholders::_1));
        RCLCPP_INFO(this->get_logger(), "Waiting on '%s' for the map -> camera_init alignment.", topic.c_str());
    }

private:
    void callback(const geometry_msgs::msg::PoseWithCovarianceStamped::SharedPtr msg)
    {
        geometry_msgs::msg::TransformStamped transform;
        transform.header.stamp = this->now();
        transform.header.frame_id = map_frame_id;
        transform.child_frame_id = odom_frame_id;
        transform.transform.translation.x = msg->pose.pose.position.x;
        transform.transform.translation.y = msg->pose.pose.position.y;
        transform.transform.translation.z = msg->pose.pose.position.z;
        transform.transform.rotation = msg->pose.pose.orientation;

        broadcaster_->sendTransform(transform);
    }

    rclcpp::Subscription<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr subscription_;
    std::shared_ptr<tf2_ros::StaticTransformBroadcaster> broadcaster_;
    std::string odom_frame_id, map_frame_id;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<TransformPublisherNode>());
    rclcpp::shutdown();
    return 0;
}
