// Copyright (c) 2023, Giang Hoang Nguyen - Institute for Artificial Intelligence, University Bremen

// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:

// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.

// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#ifdef VISUAL
#include "mj_visual.h"
#endif

#include "mj_simulate.h"
#ifdef __linux__
#include <jsoncpp/json/json.h>
#include <jsoncpp/json/reader.h>
#elif _WIN32
#include <json/json.h>
#include <json/reader.h>
#endif
#include <thread>
#include <csignal>

static MjSimulate &mj_simulate = MjSimulate::get_instance();
#ifdef VISUAL
static MjVisual &mj_visual = MjVisual::get_instance();
#endif

// Signal handler function
void signal_handler(int signum) {
    printf("Interrupt signal (%d) received.\n", signum);
    
    stop = true;

    // Exit program
    exit(signum);
}

int main(int argc, char **argv)
{
    // Register signal handler for SIGINT
    signal(SIGINT, signal_handler);

    // print version, check compatibility
    printf("MuJoCo version %s\n", mj_versionString());

    if (argc != 2)
    {
        mju_error("USAGE:  mujoco mjcf.xml\n");
    }
    scene_xml_path = argv[1];
    
    mj_simulate.init();
#ifdef VISUAL
    mj_visual.init();
#endif

    std::thread sim_thread(&MjSimulate::run, &mj_simulate);
#ifdef VISUAL
    mj_visual.run();
#endif
    
    sim_thread.join();

    return 0;
}