#!/usr/bin/env python3

import traceback
import better_exceptions

import numpy as np
import soundfile
import random
import time
import sys
import argparse

from asciimatics.screen import Screen

import SpoonModes
MODES= SpoonModes.SpoonSliceModes()
LOOP_MODES= SpoonModes.SpoonLoopModes()

from spoon_logging import D, L, W, E

from SpnAudioEngine import SpnAudioEngine
from SpnAudioLoop import SpnAudioLoop
import SpnPatchParser
from SpnPatchParser import SpnLoopFile
from SpnTUI import draw_the_tui
from SpnOSCReceiver import start_OSC_server

DESC_LONG="""
SpoonFight.py
I see you've played Knifey-Spooney before!
This is a 4 track loop player.
controlled by OSC
"""

VERSION_INFO="""

"""

DESC_NAME = """
░█▀▀░█▀█░█▀█░█▀█░█▀█░░░█▀▀░▀█▀░█▀▀░█░█░▀█▀
░▀▀█░█▀▀░█░█░█░█░█░█░░░█▀▀░░█░░█░█░█▀█░░█░
░▀▀▀░▀░░░▀▀▀░▀▀▀░▀░▀░░░▀░░░▀▀▀░▀▀▀░▀░▀░░▀░

 """
 
class SpoonFightStatus:
    # this class holds the status of the spoon fight
    """
    Attributes:
        status_message.  this is the message that goes accross the top in the banner.
        loops
        osc_port
        osc_message  this is the latest action that has been sent via OSC
        event_history  this is a history of osc and status messages
    """
    
    def __init__(self, new_osc_port):            
        
        self.status_message = "starting"    
        #dictionary to store the loops
        self.loops = {'/loop/1': None, '/loop/2': None, '/loop/3': None, '/loop/4': None }
        
        #event history
        self.event_history = [] #empty list
        self.osc_port = new_osc_port
        self.osc_message = "OSC starting"
        self.verbose_flag = False
        return

    def set_status_message(self, new_message, verbose_message=False):
        #if it's a message to display in verbose mode, verbose_message will be true and verbose_flag will be true
        if(verbose_message and not self.verbose_flag ):
            # requesting a verbose print and verbose flag is not set return doing nothing
            return
        
        self.status_message = new_message
        self.event_history.append('S: {}'.format(new_message) )
        return
    
    def set_osc_message(self, new_message, verbose_message=False):
        #if it's a message to display in verbose mode,  verbose_message will be true and verbose_flag will be true
        if(verbose_message and not self.verbose_flag ):
            # requesting a verbose print and verbose flag is not set return doing nothing
            return
        self.osc_message = new_message
        self.event_history.append('OSC: {}'.format(new_message) )
        return


# this function is now inside SpnPatchParser
def get_loop_points(audio_file):
    """returns an array of tuples
        these are the 8 slice pairs
    """
    #TODO make this a seperate class that can use different slice techniques
    slice_length = int(len(audio_file)/8  )
    points = []
    for i in range(8):
        x_x= i*slice_length, (i+1)*slice_length
        points.append(x_x)
    #set the end of the last one to be the length of the audio sample to remove any rounding errors    
    points[7] = points[6][1], len(audio_file)
    return points
    

def loop_till_forever(screen):
    global spoon_fight_status
    global audioEngine
    running=True
    while(running):
        
        #SpnTUI.draw_the_tui(screen, spoon_fight_status)
        draw_the_tui(screen, spoon_fight_status)
        
        ev = screen.get_key()
        if ev in (ord('Q'), ord('q')):
            running=False
        screen.refresh()
        time.sleep(0.05)
    
    #time.sleep(10)
    
    #if we quite clean up audio
    audioEngine.stop_audio()
    return

def main():
    
    
    parser = argparse.ArgumentParser(
    description=DESC_NAME , formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--oscport',help='Port OSC listens on', action="store", type=int, default=5080)
    parser.add_argument('--patchfile', help='Patch file to load', action="store", required=True)
    parser.add_argument('--tuirefresh',help='refresh rate for UI.  This is for slow networked shell connections', action="store", default=20)
    parser.add_argument('--configfile',help='config file to load NOT IMPLEMENTED', action="store")
    parser.add_argument('--verbose', help= 'Turn on verbose mode', action='store_true', default=False )
    parser.add_argument('--version', help='Display version information', action='version', version='%(prog)s 0.0')
    
    args = parser.parse_args()
    
    #create the audio engine
    global audioEngine
    audioEngine = SpnAudioEngine()
    
    #create the status 
    global spoon_fight_status
    spoon_fight_status = SpoonFightStatus( args.oscport)
    
    
    #create the four loops
    spoon_fight_status.loops['/loop/1'] = SpnAudioLoop('/loop/1')
    spoon_fight_status.loops['/loop/2'] = SpnAudioLoop('/loop/2')
    spoon_fight_status.loops['/loop/3'] = SpnAudioLoop('/loop/3')
    spoon_fight_status.loops['/loop/4'] = SpnAudioLoop('/loop/4')
    
    # add the loop audio to the audioengine
    for i in spoon_fight_status.loops:
        audioEngine.add_source( spoon_fight_status.loops[i].get_audio )
    
    # open patch file
    ret_loops = SpnPatchParser.SpnPatchParser(args.patchfile)
        
    i=0
    spoon_fight_status.loops['/loop/1'].set_audio_buffer( ret_loops[i].get_audio_data(),ret_loops[i].get_slice_points() )
    spoon_fight_status.loops['/loop/1'].set_audio_file_name(ret_loops[i].audio_section_name )
    
    #spoon_fight_status.loops['/loop/1'].loop_mode = LOOP_MODES.STOP
    i=1
    spoon_fight_status.loops['/loop/2'].set_audio_buffer( ret_loops[i].get_audio_data(),ret_loops[i].get_slice_points() )
    spoon_fight_status.loops['/loop/2'].set_audio_file_name(ret_loops[i].audio_section_name )
    #spoon_fight_status.loops['/loop/2'].loop_mode = LOOP_MODES.STOP
    i=2
    spoon_fight_status.loops['/loop/3'].set_audio_buffer( ret_loops[i].get_audio_data(),ret_loops[i].get_slice_points() )
    spoon_fight_status.loops['/loop/3'].set_audio_file_name(ret_loops[i].audio_section_name )
    #spoon_fight_status.loops['/loop/3'].loop_mode = LOOP_MODES.STOP
    i=3
    spoon_fight_status.loops['/loop/4'].set_audio_buffer( ret_loops[i].get_audio_data(),ret_loops[i].get_slice_points() )
    spoon_fight_status.loops['/loop/4'].set_audio_file_name(ret_loops[i].audio_section_name )
    #spoon_fight_status.loops['/loop/4'].loop_mode = LOOP_MODES.STOP
    
    # start the OSC server
    # returns a tuple of OSC server, and the thread it is in.
    local_server, local_server_thread = start_OSC_server(spoon_fight_status)
    spoon_fight_status.set_status_message("started OSC server")
                
    audioEngine.start_audio()
    spoon_fight_status.set_status_message("started audio engine")
    
    #TODO put the main loop in here.
    
    Screen.wrapper(loop_till_forever)
    
    D("shuting down threads")
    local_server.shutdown()
    D("OSC Server thread stopped")
    audioEngine.stop_audio()
    D("Audio Thread stopped")
    
    return



if __name__ == "__main__":
    main() 
 