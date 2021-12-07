
import pandas as pd
import numpy as np
import seaborn as sns
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import LocallyLinearEmbedding
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.preprocessing import scale 
from scipy.signal import savgol_filter
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import RepeatedKFold
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix
import pickle
import joblib

import LCD_1in44
import LCD_Config
from PIL import Image,ImageDraw,ImageFont,ImageColor
import RPi.GPIO as GPIO
from NIRS import NIRS
import math
import csv
from datetime import datetime
import subprocess

KEY_PRESS_PIN  = 13
KEY_LEFT_PIN   = 5
KEY_RIGHT_PIN  = 26
KEY_UP_PIN = 6
KEY_DOWN_PIN = 19
KEY1_PIN       = 21
KEY2_PIN       = 20
KEY3_PIN       = 16

#init GPIO
GPIO.setmode(GPIO.BCM) 
GPIO.cleanup()
GPIO.setup(KEY_PRESS_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
GPIO.setup(KEY_LEFT_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(KEY_RIGHT_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(KEY_UP_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(KEY_DOWN_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Input with pull-up
GPIO.setup(KEY1_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
GPIO.setup(KEY2_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
GPIO.setup(KEY3_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up

LCD = LCD_1in44.LCD()

#print "**********Init LCD**********"
Lcd_ScanDir = LCD_1in44.SCAN_DIR_DFT  #SCAN_DIR_DFT = D2U_L2R
LCD.LCD_Init(Lcd_ScanDir)
LCD.LCD_Clear()

image = Image.new("RGB", (LCD.width, LCD.height), "BLACK")
draw = ImageDraw.Draw(image)
image = Image.open('/home/pi/Mudcrab/main.bmp')
LCD.LCD_ShowImage(image,0,0)
font = ImageFont.truetype('/home/pi/Mudcrab/FreeSans.ttf', 16)
font1 = ImageFont.truetype('/home/pi/Mudcrab/FreeSans.ttf', 90)
count = 0

def showgrade(grade, prob):
    if grade == "A":
        image = Image.new("RGB", (LCD.width, LCD.height), "GREEN")
    if grade == "B":
        image = Image.new("RGB", (LCD.width, LCD.height), "YELLOW")    
    if grade == "C":
        image = Image.new("RGB", (LCD.width, LCD.height), "RED")   
    draw = ImageDraw.Draw(image)
    draw.text((45, 8), prob, fill = "WHITE", font=font)
    draw.text((32, 15), grade, fill = "WHITE", font=font1)
    image2 = image.rotate(270, expand= True)
    LCD.LCD_ShowImage(image2,0,0)

def savedata(sample):
    image = Image.new("RGB", (LCD.width, LCD.height), "BLACK") 
    draw = ImageDraw.Draw(image)
    draw.text((30, 8), "Sample", fill = "WHITE", font=font)
    tempstr = "{}".format(count)
    draw.text((90, 8), tempstr, fill = "WHITE", font=font)
    draw.text((32, 15), sample, fill = "WHITE", font=font1)
    image2 = image.rotate(270, expand= True)
    LCD.LCD_ShowImage(image2,0,0)  

while 1:
    #Key Up (left for the device) to show the current IP address for conif
    if GPIO.input(KEY_UP_PIN) == 0:
        rawIP = subprocess.check_output(["hostname","-I"])
        ip = rawIP.decode("utf-8")
        image = Image.new("RGB", (LCD.width, LCD.height), "GREEN")
        draw = ImageDraw.Draw(image)
        draw.text((10, 8), ip, fill = "WHITE", font=font)
        image2 = image.rotate(270, expand= True)
        LCD.LCD_ShowImage(image2,0,0)
    #Key press to trigger testing
    if GPIO.input(KEY_PRESS_PIN) == 0: # button is released
        test = 1
        nirs = NIRS()
        image = Image.open('/home/pi/Mudcrab/busy.bmp')
        LCD.LCD_ShowImage(image,0,0)
        nirs.set_hibernate(False)
        nirs.set_lamp_on_off(0)
        #nirs.set_pga_gain(1)
        nirs.scan()
        results = nirs.get_scan_results()        
        intensity = np.array(results['intensity'])
        wavelength = np.array(results['wavelength'])
        reference = np.array(results['reference'])
        aborbance = [0]*len(reference)
        
        for x in range(0,len(reference)-1):
            if intensity[x]/reference[x] > 0:
                aborbance[x] = -math.log10(intensity[x]/reference[x])
            
        dateTimeObj = datetime.now()
        filename = "/home/pi/Mudcrab/temp.csv"
        f = open(filename,'w')
        writer = csv.writer(f)
        writer.writerow(wavelength)
        writer.writerow(aborbance)
        f.close()
    
        data = pd.read_csv(filename)

        X = data.values[:,:]

        # y = pd.DataFrame(data.iloc[:,0])
        X = pd.DataFrame(data.iloc[:,:])

        #apply first order dericative with 25 points.
        X = savgol_filter(X, 25, polyorder = 2,deriv=1)


        #MSC Pre-processing
        for i in range(X.shape[0]):
            X[i,:] -= X[i,:].mean()   
            ref = np.mean(X, axis=0) 
        data_msc = np.zeros_like(X)
        for i in range(X.shape[0]):
            reg = np.polyfit(ref, X[i,:], 1, full=True) #regress each spectrum
            data_msc[i,:] = (X[i,:] - reg[0][1]) / reg[0][0] # MSC correction

        X = data_msc
        X= pd.DataFrame(X)
        X = X.loc[:, 1:]

        #print(X)
        loaded_model = joblib.load('/home/pi/Mudcrab/model100.sav')
        yhat = loaded_model.predict(X)
        yprob = loaded_model.predict_proba(X)[:,1]
        yprob_s = "{:.2f}".format(yprob[0])
        
        grade = "{}".format(yhat[0])
        showgrade(grade, yprob_s)  
    #Key left (down for the device) to show the absorption chart
    if GPIO.input(KEY_LEFT_PIN) == 0: # button is released
        image = Image.new("RGB", (LCD.width, LCD.height), "BLACK")
        draw = ImageDraw.Draw(image)
        coord = [0] * len(aborbance)
        for x in range(0,len(aborbance)-1):
            coord[x] = round(aborbance[x] * 63 / max(aborbance))         
        for x in range(0,len(coord)-2,2):        
            #draw.line([(round(x/2),coord[x]),(round(x/2)+1,coord[x+1])], fill = "WHITE",width = 2)
            draw.line([(coord[x],round(x/2)),(coord[x+1],round(x/2)+1)], fill = "WHITE",width = 2)

        LCD.LCD_ShowImage(image,0,0)
        LCD_Config.Driver_Delay_ms(500)       
    #Key right (Up for the device) to back to the result
    if GPIO.input(KEY_RIGHT_PIN) == 0: # button is released
        image = Image.new("RGB", (LCD.width, LCD.height), "BLACK")
        draw = ImageDraw.Draw(image)

        if yhat == 'A':
            image = Image.new("RGB", (LCD.width, LCD.height), "GREEN")
            draw = ImageDraw.Draw(image)
            draw.text((45, 8), yprob_s, fill = "WHITE", font=font)
            draw.text((32, 15), 'A ', fill = "WHITE", font=font1)
            image2 = image.rotate(270, expand= True)
            LCD.LCD_ShowImage(image2,0,0)
        if yhat == 'B':
            image = Image.new("RGB", (LCD.width, LCD.height), "YELLOW")
            draw = ImageDraw.Draw(image)
            draw.text((45, 8), yprob_s, fill = "WHITE", font=font)
            draw.text((32, 15), 'B ', fill = "WHITE", font=font1)
            image2 = image.rotate(270, expand= True)
            LCD.LCD_ShowImage(image2,0,0)
        if yhat == 'C':
            image = Image.new("RGB", (LCD.width, LCD.height), "RED")
            draw = ImageDraw.Draw(image)
            draw.text((45, 8), yprob_s, fill = "WHITE", font=font)
            draw.text((32, 15), 'C ', fill = "WHITE", font=font1)
            image2 = image.rotate(270, expand= True)
            LCD.LCD_ShowImage(image2,0,0)
    #Key_1 for setting A grade
    if GPIO.input(KEY1_PIN) == 0 and test == 1:
        dateTimeObj = datetime.now()
        timestampStr = dateTimeObj.strftime("%d-%b-%Y_%H:%M:%S")
        filename = "/home/pi/Mudcrab/data/Data_A_{}_{}.csv".format(yhat,timestampStr)
        f = open(filename,'w')
        writer = csv.writer(f)
        writer.writerow(wavelength)
        writer.writerow(aborbance)
        f.close()
        count =  count + 1
        savedata("A")
        print("A grade saved")
        test = 0
    #Key_2 for setting B grade
    if GPIO.input(KEY2_PIN) == 0 and test == 1:   
        dateTimeObj = datetime.now()
        timestampStr = dateTimeObj.strftime("%d-%b-%Y_%H:%M:%S")
        filename = "/home/pi/Mudcrab/data/Data_B_{}_{}.csv".format(yhat,timestampStr)
        f = open(filename,'w')
        writer = csv.writer(f)
        writer.writerow(wavelength)
        writer.writerow(aborbance)
        f.close()
        count =  count + 1
        savedata("B")
        print("B grade saved")
        test = 0
    #Key_3 for setting C grade
    if GPIO.input(KEY3_PIN) == 0 and test == 1:
        dateTimeObj = datetime.now()
        timestampStr = dateTimeObj.strftime("%d-%b-%Y_%H:%M:%S")
        filename = "/home/pi/Mudcrab/data/Data_C_{}_{}.csv".format(yhat,timestampStr)
        f = open(filename,'w')
        writer = csv.writer(f)
        writer.writerow(wavelength)
        writer.writerow(aborbance)
        f.close()
        count =  count + 1
        savedata("C")
        print("C grade saved")
        test = 0