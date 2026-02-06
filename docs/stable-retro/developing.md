# Development[¶](https://stable-retro.farama.org/developing/#development "Link to this heading")

Adding new games can be done without recompiling Stable Retro, but if you need to work on the C++ code or make changes to the UI, you will want to compile Stable Retro from source.

## Install Retro from source[¶](https://stable-retro.farama.org/developing/#install-retro-from-source "Link to this heading")

Building Stable Retro requires at least either gcc 5 or clang 3.4.

### Prerequisites[¶](https://stable-retro.farama.org/developing/#prerequisites "Link to this heading")

To build Stable Retro you must first install CMake. You can do this either through your package manager, download from the [official site](https://cmake.org/download/) or `pip3 install cmake`. If you’re using the official installer on Windows, make sure to tell CMake to add itself to the system PATH.

### Mac prerequisites[¶](https://stable-retro.farama.org/developing/#mac-prerequisites "Link to this heading")

Since LuaJIT does not work properly on macOS you must first install Lua 5.1 from homebrew:

brew install pkg-config lua@5.1

### Windows prerequisites[¶](https://stable-retro.farama.org/developing/#windows-prerequisites "Link to this heading")

Install docker

### Linux prerequisites[¶](https://stable-retro.farama.org/developing/#linux-prerequisites "Link to this heading")

sudo apt-get install zlib1g-dev

### Building Linux and Mac[¶](https://stable-retro.farama.org/developing/#building-linux-and-mac "Link to this heading")

git clone https://github.com/farama-foundation/stable-retro.git stable-retro
cd stable-retro
pip3 install \-e .

### Building Windows[¶](https://stable-retro.farama.org/developing/#building-windows "Link to this heading")

Run the following

docker/build\_windows.bat

Once complete use docker cp to copy the whl file out of the container.

Then you may pip install

git clone https://github.com/farama-foundation/stable-retro.git stable-retro
cd stable-retro
pip3 install \-e .

## Install Retro UI from source[¶](https://stable-retro.farama.org/developing/#install-retro-ui-from-source "Link to this heading")

First make sure you can install Retro from source, after that follow the instructions for your platform:

### macOS[¶](https://stable-retro.farama.org/developing/#macos "Link to this heading")

Note that for Mojave (10.14) you may need to install `/Library/Developer/CommandLineTools/Packages/macOS_SDK_headers_for_macOS_10.14.pkg`

brew install pkg-config capnp lua@5.1 qt5
cmake . \-DCMAKE\_PREFIX\_PATH\=/usr/local/opt/qt \-DBUILD\_UI\=ON \-UPYLIB\_DIRECTORY
make \-j$(sysctl hw.ncpu | cut \-d: \-f2)
open "Gym Retro Integration.app"

### Linux[¶](https://stable-retro.farama.org/developing/#linux "Link to this heading")

sudo apt-get install capnproto libcapnp-dev libqt5opengl5-dev qtbase5-dev zlib1g-dev
cmake . \-DBUILD\_UI\=ON \-UPYLIB\_DIRECTORY
make \-j$(grep \-c ^processor /proc/cpuinfo)
./gym-retro-integration

### Windows[¶](https://stable-retro.farama.org/developing/#windows "Link to this heading")

The Retro UI is not currently supported in native Windows but you can use it easily via WSL2 (Windows Subsystem for Linux) by following the instructions above for Linux. From within WSL2 just launch gym-retro-integration binary like you would on linux.