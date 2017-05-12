#!/bin/sh
# monitor-agent start script

ERROR_REPORT=false
PIP_VERSION="6.1.1"

# Bail on errors
set -e
# We shouldn't have unbounded vars
set -u
set +u
APP_KEY=${APP_KEY:-no_key}
SECERT_KEY=${SECERT_KEY:-no_key}
START_AGENT=${START_AGENT:-1}


# If MONITOR_HOME is unset
if [ -z "$MONITOR_HOME" ]; then
    # Compatibilty: MONITOR_HOME used in lieu of MONITOR_HOME
    if [ -n "$monitor_home" ]; then
        MONITOR_HOME="$monitor_home"
    else
        cur="$(cd `dirname $0`; pwd)"
        MONITOR_HOME=$cur
    fi
fi

print_console() {
    ct=`date +"%m-%d %H:%M:%S"`
    printf "$ct %s\n" "$*" | tee -a "$LOGFILE" >&3
}

print_console_wo_nl() {
    printf "%s" "$*" | tee -a "$LOGFILE" >&3
}

print_red() {
    printf "\033[31m%s\033[0m\n" "$*" | tee -a "$LOGFILE" >&3
}

print_green() {
    printf "\033[32m%s\033[0m\n" "$*" | tee -a "$LOGFILE" >&3
}

print_done() {
    print_green "Done"
}

# Will be called if an unknown error appears and that the Agent is not running
# It asks the user if he wants to automatically send a failure report
error_trap() {
    print_red "It looks like you hit an issue when trying to install the monitor agent."
    print_console "###"
    if [ -n "$ERROR_MESSAGE" ]; then
        print_red "$ERROR_MESSAGE"
    else
        tail -n 5 "$LOGFILE" | tee -a "$LOGFILE" >&3
    fi
}

# Catch errors and handle them
trap error_trap INT TERM
trap '[ "$?" -eq 0 ] || error_trap' EXIT

LOGFILE="$MONITOR_HOME/agent-install.log"
BASE_LOG_DIR='/var/log/monitor-agent'
exec 3>&1 1>$LOGFILE 2>&1
print_console "install monitor-agent!"

mkdir -p $BASE_LOG_DIR

#######################################################################
# CHECKING REQUIREMENTS
#######################################################################
detect_python() {
    if command -v python2.7; then
        export PYTHON_CMD="python2.7"
    elif command -v python2; then
        # FreeBSD apparently uses this
        export PYTHON_CMD="python2"
    else
        export PYTHON_CMD="python"
    fi
}

detect_downloader() {
    if command -v curl; then
        export DOWNLOADER="curl -k -L -o"
        export HTTP_TESTER="curl -f"
    elif command -v wget; then
        export DOWNLOADER="wget -O"
        export HTTP_TESTER="wget -O /dev/null"
    fi
}

detect_sed() {
    if command -v sed; then
        export SED_CMD="sed"
    fi
}

print_console "Checking installation requirements"

# Sysstat must be installed, except on Macs
ERROR_MESSAGE="sysstat is not installed on your system
If you run CentOs/RHEL, you can install it by running:
  sudo yum install sysstat
If you run Debian/Ubuntu, you can install it by running:
  sudo apt-get install sysstat"

if [ "$(uname)" != "Darwin" ]; then
    iostat > /dev/null 2>&1
fi
print_green "* sysstat is installed"

# Detect Python version
ERROR_MESSAGE="Python 2.6 or 2.7 is required to install the agent from source"
detect_python
if [ -z "$PYTHON_CMD" ]; then exit 1; fi
$PYTHON_CMD -c "import sys; exit_code = 0 if sys.version_info[0]==2 and sys.version_info[1] > 5 else 66 ; sys.exit(exit_code)" > /dev/null 2>&1
print_green "* python found, using \`$PYTHON_CMD\`"

#######################################################################
# INSTALLING
#######################################################################
print_console
print_console
print_console "Installing Monitor Agent $AGENT_VERSION"
print_console "Installation is logged at $LOGFILE"
print_console

# The steps are detailed enough to know where it fails
ERROR_MESSAGE=""

print_console "* Setting up a python virtual env"
$PYTHON_CMD "$MONITOR_HOME/utils/virtualenv.py" --system-site-packages --no-pip --no-setuptools "$MONITOR_HOME/venv"
print_done

print_console "* Activating the virtual env"
# venv activation script doesn't handle -u mode
set +u
. "$MONITOR_HOME/venv/bin/activate"
set -u
print_done

VENV_PYTHON_CMD="$MONITOR_HOME/venv/bin/python"
VENV_PIP_CMD="$MONITOR_HOME/venv/bin/pip"

print_console "* Setting up setuptools"
$VENV_PYTHON_CMD "$MONITOR_HOME/packaging/ez_setup.py" --to-dir=$MONITOR_HOME
print_done

# supervisord.conf uses relative paths so need to chdir
cd "$MONITOR_HOME"
if $ERROR_REPORT;then
    nohup $VENV_PYTHON_CMD forwarder.py 1>/dev/null 2>>$LOGFILE &
    AGENT_FORWARDER_PID=$!
    nohup $VENV_PYTHON_CMD collector.py 1>/dev/null 2>>$LOGFILE &
    AGENT_PID=$!
else
    nohup $VENV_PYTHON_CMD forwarder.py 1>/dev/null 2>&1 &
    AGENT_FORWARDER_PID=$!
    nohup $VENV_PYTHON_CMD collector.py 1>/dev/null 2>&1 &
    AGENT_PID=$!
fi
print_console "* forwarder pid is $AGENT_FORWARDER_PID"
print_console "* agent pid is $AGENT_PID"
cd -
sleep 1

# Checking that the agent is up
if ! kill -0 $AGENT_FORWARDER_PID; then
    ERROR_MESSAGE="Failure when launching AGENT_FORWARDER"
    exit 1vim
fi
if ! kill -0 $AGENT_PID; then
    ERROR_MESSAGE="Failure when launching AGENT_PID"
    exit 1
fi
print_green "    - monitor agent started"

