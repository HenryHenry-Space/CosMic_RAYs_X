execute_process(COMMAND "/home/xhnfly/Cosmic_rays_X/X_ROS/build/X_UR/UR5_driver/ur_kinematics/catkin_generated/python_distutils_install.sh" RESULT_VARIABLE res)

if(NOT res EQUAL 0)
  message(FATAL_ERROR "execute_process(/home/xhnfly/Cosmic_rays_X/X_ROS/build/X_UR/UR5_driver/ur_kinematics/catkin_generated/python_distutils_install.sh) returned error code ")
endif()
