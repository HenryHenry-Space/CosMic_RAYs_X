#!/bin/sh

if [ -n "$DESTDIR" ] ; then
    case $DESTDIR in
        /*) # ok
            ;;
        *)
            /bin/echo "DESTDIR argument must be absolute... "
            /bin/echo "otherwise python's distutils will bork things."
            exit 1
    esac
fi

echo_and_run() { echo "+ $@" ; "$@" ; }

echo_and_run cd "/home/xhnfly/Cosmic_rays_X/X_ROS/src/X_UR/ee_ur5e/gripper/robotiq_modbus_rtu"

# ensure that Python install destination exists
echo_and_run mkdir -p "$DESTDIR/home/xhnfly/Cosmic_rays_X/X_ROS/install/lib/python2.7/dist-packages"

# Note that PYTHONPATH is pulled from the environment to support installing
# into one location when some dependencies were installed in another
# location, #123.
echo_and_run /usr/bin/env \
    PYTHONPATH="/home/xhnfly/Cosmic_rays_X/X_ROS/install/lib/python2.7/dist-packages:/home/xhnfly/Cosmic_rays_X/X_ROS/build/lib/python2.7/dist-packages:$PYTHONPATH" \
    CATKIN_BINARY_DIR="/home/xhnfly/Cosmic_rays_X/X_ROS/build" \
    "/usr/bin/python2" \
    "/home/xhnfly/Cosmic_rays_X/X_ROS/src/X_UR/ee_ur5e/gripper/robotiq_modbus_rtu/setup.py" \
     \
    build --build-base "/home/xhnfly/Cosmic_rays_X/X_ROS/build/X_UR/ee_ur5e/gripper/robotiq_modbus_rtu" \
    install \
    --root="${DESTDIR-/}" \
    --install-layout=deb --prefix="/home/xhnfly/Cosmic_rays_X/X_ROS/install" --install-scripts="/home/xhnfly/Cosmic_rays_X/X_ROS/install/bin"
