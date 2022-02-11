"""
Main Scratch2Python file

This file is used to run Scratch2Python and build the project based on the data given by sb3Unpacker.py

Copyright (C) 2022 Secret-chest and other contributors (copyright applies for all files)

Scratch2Python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

__version__ = "M12 (development version)"
__author__ = "Secret-chest"

import platform
import tkinter.simpledialog
from platform import system, platform
import os
import sys
from typing import Tuple

import config

if system() == "Linux":
    OS = "linux"
elif system() == "Darwin":
    OS = "macOSX"
elif system() == "Windows":
    OS = "windows"
else:
    OS = "unknown"


if not config.enableTerminalOutput:
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")
if not config.enableDebugMessages:
    sys.stderr = open(os.devnull, "w")

print(f"Scratch2Python {__version__} running on {OS}")

if OS == "windows":
    os.environ["path"] += r";cairolibs"

if OS == "unknown":
    print(f"Sorry, Scratch2Python does not recognize your OS. Your platform string is: {platform()}", file=sys.stderr)

sys.stdout = open(os.devnull, "w")
import io
import sb3Unpacker
from sb3Unpacker import *
import shutil
import scratch
import pygame
import time
import tkinter as tk
from pathlib import Path
from tkinter.messagebox import *
from tkinter.simpledialog import *
from tkinter import filedialog
from targetSprite import TargetSprite
sys.stdout = sys.__stdout__

if not config.enableTerminalOutput:
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")
if not config.enableDebugMessages:
    sys.stderr = open(os.devnull, "w")

# Start tkinter for showing some popups, and hide main window
mainWindow = tk.Tk()
mainWindow.withdraw()

if config.projectLoadMethod == "manual":
    setProject = config.projectFileName
elif config.projectLoadMethod == "cmdline":
    try:
        setProject = sys.argv[1]
    except IndexError:
        raise OSError("No project file name passed")
elif config.projectLoadMethod == "interactive":
    setProject = input("Project file name: ")
elif config.projectLoadMethod == "filechooser":
    fileTypes = [("Scratch 3 projects", ".sb3"), ("All files", ".*")]
    setProject = filedialog.askopenfilename(parent=mainWindow,
                                            initialdir=os.getcwd(),
                                            title="Choose a project to load",
                                            filetypes=fileTypes)
else:
    sys.stderr = sys.__stderr__
    raise config.ConfigError("Invalid setting: projectLoadMethod")

# Get project data and create sprites
targets, project = sb3Unpacker.sb3Unpack(setProject)
allSprites = pygame.sprite.Group()
for t in targets:
    sprite = TargetSprite(t)
    t.sprite = sprite
    allSprites.add(sprite)
    sprite.setXy(t.x, t.y)

# Start pygame, load fonts and print a debug message
pygame.init()
font = pygame.font.SysFont(pygame.font.get_default_font(), 16)
fontXl = pygame.font.SysFont(pygame.font.get_default_font(), 36)

# Create paused message
paused = fontXl.render("Paused (Press F6 to resume)", True, (0, 0, 0))
pausedWidth, pausedHeight = fontXl.size("Paused (Press F6 to resume)")

# Set player size and key delay
HEIGHT = config.projectScreenHeight
WIDTH = config.projectScreenWidth
KEY_DELAY = 500

# Get project name and set icon
projectName = Path(setProject).stem
icon = pygame.image.load("icon.svg")

# Create project player and window
display = pygame.display.set_mode([WIDTH, HEIGHT])
pygame.display.set_caption(projectName + " - Scratch2Python" + " " + __version__)
pygame.display.set_icon(icon)

# Extract if requested
if config.extractOnProjectRun:
    print("Extracting project")
    shutil.rmtree("assets")
    os.mkdir("assets")
    project.extractall("assets")

# Set running state
projectRunning = True
isPaused = False

# Initialize clock
clock = pygame.time.Clock()

# Clear display
display.fill((255, 255, 255))

doScreenRefresh = False


# Define a dialog class for screen resolution
class SizeDialog(tkinter.simpledialog.Dialog):
    def __init__(self, parent: tk.Misc | None, title):
        super().__init__(parent, title)

    def body(self, master) -> tuple[str, str]:
        tk.Label(master, text="Width: ").grid(row=0)
        tk.Label(master, text="Height: ").grid(row=1)

        self.width = tk.Entry(master)
        self.height = tk.Entry(master)

        self.width.grid(row=0, column=1)
        self.height.grid(row=1, column=1)

        return self.width

    def okPressed(self):
        self.setWidth = self.width.get()
        self.setHeight = self.height.get()
        self.destroy()

    def cancelPressed(self):
        self.destroy()

    def buttonbox(self):
        self.okButton = tk.Button(self, text='OK', width=5, command=self.okPressed)
        self.okButton.pack(side="left")
        cancelButton = tk.Button(self, text='Cancel', width=5, command=self.cancelPressed)
        cancelButton.pack(side="right")
        self.bind("<Return>", lambda event: self.okPressed())
        self.bind("<Escape>", lambda event: self.cancelPressed())

# Start project
toExecute = []
eventHandlers = []
print("Project started")
# Start green flag scripts
for s in allSprites:
    for _, block in s.target.blocks.items():
        if block.opcode == "event_whenflagclicked":
            nextBlock = scratch.execute(block, block.target.sprite)
            # Error-proof by checking if the scripts are not empty
            if nextBlock:
                # Add the next block to the queue
                toExecute.append(nextBlock)
        elif block.opcode.startswith("event_"):  # add "when I start as a clone" code later
            eventHandlers.append(block)

# Mainloop
while projectRunning:
    # Process Pygame events
    for event in pygame.event.get():
        # Window quit (ALT-F4 / X button)
        if event.type == pygame.QUIT:
            print("Player closed")
            projectRunning = False

        # Debug and utility functions
        keysRaw = pygame.key.get_pressed()
        keys = set(k for k in scratch.KEY_MAPPING.values() if keysRaw[k])

        if pygame.K_F1 in keys:  # Help
            showinfo("Help", "Nothing to see here")
        if pygame.K_F2 in keys:  # Scratch2Python options
            showinfo("Options", "Nothing to see here")
        if pygame.K_F3 in keys:  # Debug
            showinfo("Debug", "Nothing to see here")
        if pygame.K_F4 in keys:  # Project info
            showinfo("Project info", "Nothing to see here")
        if pygame.K_F5 in keys:  # Extract
            confirm = askokcancel("Extract", "Extract all project files?")
            if confirm:
                print("Extracting project")
                shutil.rmtree("assets")
                os.mkdir("assets")
                project.extractall("assets")
        if pygame.K_F6 in keys:  # Pause
            isPaused = not isPaused
        if pygame.K_F7 in keys:  # Set new FPS
            # Open dialog
            newFPS = askinteger(title="FPS", prompt="Enter new FPS")
            if newFPS is not None:
                print("FPS set to", newFPS)
                config.projectMaxFPS = newFPS
        if pygame.K_F8 in keys:  # Set new screen resolution
            try:
                # Open special dialog
                dialog = SizeDialog(mainWindow, title="Screen resolution")
                config.projectScreenWidth = int(dialog.setWidth)
                config.projectScreenHeight = int(dialog.setHeight)

                # Redraw everything and recalculate sprite operations
                display = pygame.display.set_mode([config.projectScreenWidth, config.projectScreenHeight])
                HEIGHT = config.projectScreenHeight
                WIDTH = config.projectScreenWidth
                scratch.refreshScreenResolution()
                for s in allSprites:
                    s.setXy(s.x, s.y)
                print("Screen resolution set to", str(HEIGHT) + "x" + str(WIDTH))
            except ValueError:
                pass

    display.fill((255, 255, 255))
    if toExecute:
        for block in toExecute:
            pass
            # print("Running block", block.blockID, "of type", block.opcode)
    if not isPaused:
        for e in eventHandlers:
            if e.opcode == "event_whenkeypressed" and keys:
                # TODO
                # nextBlock = scratch.execute(block, block.target.sprite, keys)
                # if nextBlock:
                #     if isinstance(nextBlock, list):
                #         nextBlocks.extend(nextBlock)
                #     else:
                #         nextBlocks.append(nextBlock)
                pass
        while toExecute and not doScreenRefresh:
            # Run blocks
            nextBlocks = []
            for block in toExecute:
                if block.waiting:
                    block.executionTime += clock.get_time()
                    if block.executionTime >= block.timeDelay:
                        block.waiting = False
                        if block.opcode.startswith("event"):
                            block.blockRan = False
                        else:
                            block.blockRan = True
                        nextBlocks.append(block.target.blocks[block.next])
                        block.executionTime, block.timeDelay = 0, 0
                if not block.blockRan:
                    nextBlock = scratch.execute(block, block.target.sprite, keys)
                    if nextBlock:
                        if isinstance(nextBlock, list):
                            nextBlocks.extend(nextBlock)
                        else:
                            nextBlocks.append(nextBlock)
                if block.screenRefresh:
                    doScreenRefresh = True
            toExecute = list(set(nextBlocks))

        allSprites.draw(display)
        allSprites.update()
    else:
        display.blit(paused, (WIDTH // 2 - pausedWidth // 2, WIDTH // 2 - pausedHeight // 2))
    pygame.display.flip()
    mainWindow.update()
    doScreenRefresh = False
    clock.tick(config.projectMaxFPS)
pygame.quit()
