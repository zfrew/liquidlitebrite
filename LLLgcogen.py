from PIL import Image
import sys
from pathlib import Path

if len(sys.argv) < 2:
	sys.exit("Error: Input and/or output filenames not provided")

input_filename = Path(sys.argv[1]) # declare the input file and make sure that it exists
if not input_filename.is_file():
	sys.exit("Error: The input file %s does not exist" % input_filename)

output_filename = Path(sys.argv[2]) # specify the output filename

im = Image.open(input_filename) # assign the image to the "im" variable
px = im.load() # load the image
#print(px[0,0]) # test to verify the image is loaded

### START RGB TO CYMK CONVERSION ###
### Inputs a 3 variable list consisting of RGB and outputs a 4 variable list consisting of CMYK ###

RGB_SCALE = 255
CMYK_SCALE = 100

def rgb_to_cmyk(rgb):
    r = rgb[0]
    g = rgb[1]
    b = rgb[2]
    if (r, g, b) == (0, 0, 0):
        return 0, 0, 0, CMYK_SCALE

    c = 1 - r / RGB_SCALE
    m = 1 - g / RGB_SCALE
    y = 1 - b / RGB_SCALE

    min_cmy = min(c, m, y)
    c = (c - min_cmy) / (1 - min_cmy)
    m = (m - min_cmy) / (1 - min_cmy)
    y = (y - min_cmy) / (1 - min_cmy)
    k = min_cmy

    return int(c * CMYK_SCALE), m * CMYK_SCALE, y * CMYK_SCALE, k * CMYK_SCALE

### END RGB TO CYMK CONVERSION ###


### START EXTRUSION LEGNTHS CALCULATIONS AND ASSIGNMENTS ###

xpixel = 0 
ypixel = 0 
j = 0 
pixdirection = 0
jlookup =  {}

while j < 383: # assign pixels to a number "j" to be used as a dictionary key later
    if xpixel == 0 and ypixel == 0: 
        jlookup[j] = xpixel, ypixel
        xpixel += 1 
        j += 1
        jlookup[j] = xpixel, ypixel

    if int(xpixel) == 23:
        jlookup[j] = xpixel, ypixel 
        ypixel += 1
        pixdirection = 1
        j += 1
        jlookup[j] = xpixel, ypixel
        
    if int(xpixel) == 0:
        jlookup[j] = xpixel, ypixel
        ypixel += 1
        pixdirection = 0 
        j += 1
        jlookup[j] = xpixel, ypixel
    
    if pixdirection == 1:
        xpixel -= 1 
        j += 1    
        jlookup[j] = xpixel, ypixel

    if pixdirection == 0:
        xpixel += 1
        j += 1
        jlookup[j] = xpixel, ypixel

extrusion_lookup = {}
k = 0
saturation = 4.67 # this variable reduces the amount of white in the image thus increasing saturation. Set this value to 3.6 for true CYMK.

while k < 384: # assigns the extrusion length for each color (CYMKW) to the corresponding pixel number
    cmyk = (rgb_to_cmyk(px[(jlookup[k][0]),(jlookup[k][1])]))
    e_c = (cmyk[0] / 400) * saturation
    e_m = (cmyk[1] / 400) * saturation
    e_y = (cmyk[2] / 400) * saturation
    e_k = (cmyk[3] / 400) * saturation
    e_w = 3.5 - (e_c + e_m + e_y + e_k) 
    #print((e_c + e_m + e_y + e_k) + e_w)  # verify that all of the extrusion lengths sum to 3.5 which is the max extrusion length for a single well
    if e_w < 0: 
        print("warning, reduce saturation")
    extrusion_lookup[str(k) + "c"] = e_c
    extrusion_lookup[str(k) + "m"] = e_m
    extrusion_lookup[str(k) + "y"] = e_y
    extrusion_lookup[str(k) + "k"] = e_k
    extrusion_lookup[str(k) + "w"] = e_w
    k += 1

### END EXTRUSION LEGNTHS CALCULATIONS AND ASSIGNMENTS ###


### START GCODE PATH GENERATOR ###

f = open(output_filename, "w") # open the file for writing
f.write("M954 C310 M310 Y325 K315 W315 \n") # Servo command that opens the "C" servo channel and closes all of the others

x = 118 # X axis position for 1st pixel (0th index)
y = 91.6 # Y axis position for 1st pixel (0th index)
direction = 0
e_counter = 0 # counts extrusion lengths for gcode absolute mode
i = 0
current_color = ["c", "y", "m", "k", "w"]
color_counter = 0

while i < 384: 

    if direction == 1:
        x += 4.5
        
    if direction == 0 and i > 0: 
        x -= 4.5

    if x == 118: 
        direction = 0

    if x == 14.5:
        direction = 1
        y -= 4.5

    if x == 118:
        if i > 1:
            y -= 4.5

    if i == 0:
        e_counter = e_counter + float(extrusion_lookup[str(i) + str(current_color[color_counter])]) 
        i += 1
        f.write("G0 " + "X" + str(round(x, 2)) + " " "Y" + str(round(y, 2)) +  " " + "F10000 \n" + "G0 Z8 F1000 \n" + "G0 E" + str(round(e_counter, 2)) + "\n" + "G0 Z4 F10000 \n \n")
        
    if x != 118:
        if x != 14.5:
            e_counter = e_counter + float(extrusion_lookup[str(i) + str(current_color[color_counter])])
            i += 1
            f.write("G0 " + "X" + str(round(x, 2)) + " " "Y" + str(round(y, 2)) +  " " + "F10000 \n" + "G0 Z8 F1000 \n" + "G0 E" + str(round(e_counter, 2)) + "\n"  + "G0 Z4 F10000 \n \n")

    if x == 118 or x == 14.5: 
        if i > 1:
            e_counter = e_counter + float(extrusion_lookup[str(i) + str(current_color[color_counter])])
            f.write("G0 " + "X" + str(round(x, 2)) + " " + "F10000 \n" + "G0 Z8 F1000 \n" + "G0 E" + str(round(e_counter, 2)) + "\n" + "G0 Z4 F10000 \n \n")
            i += 1
            if i == 384 and color_counter < 5: # color purge handling 
                color_counter += 1
                i = 0 # reset i counter
                x = 118 # reset x counter
                y = 91.6  # reset y counter
                e_counter += 250 # purge current color
                f.write("G0 X10 \n")
                f.write("G0 Y0 \n")
                f.write("G0 Z30 \n")
                if color_counter == 1:
                    f.write("M954 C155 M130 Y325 K315 W315 \n") #M open
                if color_counter == 2:
                    f.write("M954 C155 M310 Y155 K315 W315 \n") #Y open
                if color_counter == 3:
                    f.write("M954 C155 M310 Y325 K140 W315 \n") #K open
                if color_counter == 4:
                    f.write("M954 C155 M310 Y325 K315 W140 \n") #W open
                f.write("G0 E" + str(round(e_counter, 2)) + "\n")
                f.write("G0 Z0 \n \n")
            if color_counter == 5:
                break
            e_counter = e_counter + float(extrusion_lookup[str(i) + str(current_color[color_counter])])
            i += 1
            f.write("G0 " + "X" + str(round(x, 2)) + " " + "Y" + str(round(y, 2)) + " " + "F10000 \n" + "G0 Z8 F1000 \n" + "G0 E" + str(round(e_counter, 2)) + "\n" +"G0 Z4 F10000 \n \n")

### END GCODE PATH GENERATOR

