#!/usr/bin/env python
#This is script is for Spectroscopic reduction of HCT spectras



import os
import os.path
import shutil
import glob
import pyfits
import numpy as np
import sys, traceback 

def Spectroscopy() :
    iraf.noao(_doprint=0) 
    iraf.twodspec(_doprint=0) 
    iraf.onedspec(_doprint=0) 
    iraf.apextract(_doprint=0)
    iraf.apextract.unlearn()
    iraf.apall.unlearn()
    iraf.apsum.unlearn()
    iraf.reidentify.unlearn()
    iraf.apextract.setParam('dispaxis',DISPAXIS)
    iraf.cd(MotherDIR)
    try :
        directories=open(MotherDIR+'/directories','r')
    except IOError :
        #Creating a text file containg the directories to visit if it doesn't already exist
        os.system('''cut -d' ' -f 1 Images4Spec.in | awk 'BEGIN{FS="/";OFS="/"}{$NF="" ; print $0}' | sort | uniq > directories ''')
        directories=open(MotherDIR+'/directories','r')
    for direc in directories.readlines():
        direc=direc.rstrip()
        iraf.cd(MotherDIR+'/'+direc)        
        print("Directory = "+direc)
        fooLamps=open('LampSpectras.txt','r')
        LampsofNight=fooLamps.readlines()
        fooLamps.close()
        fooStars=open('StarSpectras.txt','r')
        for starline in fooStars.readlines():
            starline=starline.rstrip()
            img=starline.split()[0]
            pyfits.convenience.setval(img,'DISPAXIS',DISPAXIS)
            print("Working on image "+direc+" "+starline)
            # Running apall
            iraf.apall(input=img,nfind=1,b_sample=BACKGROUND,background ='fit',weights ='variance',readnoi=READNOISE,gain=EPADU,t_function=TRACEFUNC,t_order=TRACEORDER,t_niterate=1,ylevel=APPERTURE,interactive=VER)   
            # Find the Lamp which matches the Grism from LampsofNight array
#            hdulist=pyfits.open(img)
#            GrismID=hdulist[0].header.get(GRISMHDR)
#            hdulist.close()
            GrismID=' '.join(starline.split()[1:4])    # Because for HCT the Grism header is "3 Grism 8" etc..
            yxdim=pyfits.getdata(img).shape
            Lampimg=''
            for lampline in LampsofNight :
                lampyxdim=eval(''.join(lampline.rstrip().split()[-2:]))  # The tuple of xydim of lamp
                if lampline.find(GrismID) != -1 and yxdim[0] <= lampyxdim[0] and yxdim[1] <= lampyxdim[1]  : # Hurray, Found the Arc Lamp
                    Lampimg=lampline.split()[0]
                    Lampname=lampline.split()[1]
                    break
            if Lampimg=='' :
                print ("No lamp found for calibrating "+img+" taken in Grism: "+GrismID)
                continue
            
            if not os.path.exists(Lampimg[:-4]+'ms.fits') :   #If the arc spectra is not already extracted and calibrated
                # Calling apsum
                iraf.apsum(input=Lampimg,references=img[:-5],interactive=VER,find='no',recenter='no',resize='no',edit='no',trace='no',fittrace='no',readnoise=READNOISE,gain=EPADU)
                # Copying the Master calibrated lamps spec and it's id file to database.
                LampRepofile=open(MotherDIR+'/LampRepo/LampDataBase.txt','r')
                RepoLamp=''
                for RepoLampline in LampRepofile.readlines():
                    if RepoLampline.find(Lampname+' '+GrismID) != -1 : #Hurray, found the Master calibrated lamp in Repo
                        RepoLamp=RepoLampline.split()[0]
                        shutil.copy(MotherDIR+'/LampRepo/'+RepoLamp+'.fits', RepoLamp+'.fits')
                        shutil.copy(MotherDIR+'/LampRepo/database/id'+RepoLamp, 'database/')
                        break
                LampRepofile.close()
                # Use reidentify to identify the lines in the Lamp
                if RepoLamp != '' :
                    iraf.reidentify(reference=RepoLamp, images=Lampimg[:-4]+'ms',verbose='yes',interactive=VER)
                else : 
                    print('No calibrated lamp found in LampRepo/ for calibrating '+Lampimg)
                    continue
                
            #Edit the header of img to add ref lamp
            iraf.hedit(img[:-4]+'ms.fits', "REFSPEC1",Lampimg[:-4]+'ms.fits', add=1, ver=0)
            # dispcor to apply the callibration
            iraf.dispcor(input=img[:-4]+'ms.fits',output='S'+img[:-4]+'ms.fits')





def Normalise_Counts():
    iraf.noao(_doprint=0) 
    iraf.onedspec(_doprint=0) 
    iraf.continuum.unlearn()

    iraf.cd(MotherDIR)
    directories=open(MotherDIR+'/directories','r')
    for direc in directories.readlines():
        direc=direc.rstrip()
        iraf.cd(MotherDIR+'/'+direc)        
        Specs2Norm=glob.glob('Szs*.ms.fits')
        for spec in Specs2Norm:
            iraf.continuum(input=spec,output='N'+spec,interactive=VER,function=NORMFUNC, order=NORMORDER)
    print('Normalised counts spectra created: N* ')
    iraf.cd(MotherDIR)
        
def Flux_Calibration():  #UNDER Construction...
    iraf.cd(MotherDIR)
    directories=open(MotherDIR+'/directories','r')
    for direc in directories.readlines():
        direc=direc.rstrip()
        iraf.cd(MotherDIR+'/'+direc)        

    

def Lamp_identify_subrout() :
    if os.path.exists(MotherDIR+'/LampRepo/CALIBRATED'):
        print('You seems to have already calibrated lamps in LampRepo.')
        print('Remove /LampRepo/CALIBRATED file to do calibratin in this directory')
        return()
    
    iraf.cd(MotherDIR+'/LampRepo/')
#    os.system("mkdir -p LampRepo/")
    # First copy a spectra of the lamp into LampRepo directory
    foo=open('Lamps.list','r')
    Lamps=[lamp.rstrip().split() for lamp in foo.readlines() ] #List of Lamps and stars to calibrate
    foo.close()
#    try :
#        directoriesFile=open(MotherDIR+'/directories','r')
#    except IOError :
        #Creating a text file containg the directories to visit if it doesn't already exist
#        os.system('''cut -d' ' -f 1 Images4Spec.in | awk 'BEGIN{FS="/";OFS="/"}{$NF="" ; print $0}' | sort | uniq > directories ''')
#        directoriesFile=open(MotherDIR+'/directories','r')
#    directories=[direc.rstrip() for direc in directoriesFile.readlines() ]
#    directoriesFile.close()
#    grismLIST=[]
#    LampnameArray=[]
#    for direc in directories:
#        if len(Lamps) == 0 : break
#        os.chdir(MotherDIR+'/'+direc)        
#        fooLamp=open('LampSpectras.txt','r')
#        for lampline in fooLamp.readlines():
#            lampline=lampline.rstrip()
#            lampname=lampline.split()[1]
#            hdulist=pyfits.open(lampline.split()[0])
#            GrismID=hdulist[0].header.get(GRISMHDR)
#            hdulist.close()
#            if lampname+' '+str(GrismID) in Lamps :
#                os.system('cp '+lampline.split()[0]+' '+MotherDIR+'/LampRepo/')
#                Lamps.remove(lampname+' '+str(GrismID))  #Removing from wanted list
#                if not str(GrismID) in grismLIST : 
#                    grismLIST.append(str(GrismID))
#                    LampnameArray.append([])
#                LampnameArray[grismLIST.index(str(GrismID))].append(lampline.split()[0])  #Classifying names according to Grism in array
#        fooLamp.close()
#    os.chdir(MotherDIR+'/LampRepo/')
    #Now We have to do the dispersion calibration of these spectras
    iraf.noao(_doprint=0)
    iraf.onedspec(_doprint=0) 
    iraf.twodspec(_doprint=0) 
    iraf.apextract(_doprint=0) 
    iraf.apextract.unlearn()
    iraf.apall.unlearn()
    iraf.apsum.unlearn()
    iraf.identify.unlearn()
    iraf.apextract.setParam('dispaxis',DISPAXIS)

    #Copy a good same size star spctra to quickly get a referance image for calibrating lamp.
    #For each Grism we will take star spectra of that grism.
    fooLampData=open('LampDataBase.txt','w')
#    for grism in grismLIST :
#        Found='no'
#        i=0
#        while Found == 'no' :
#            foo=open(MotherDIR+'/'+directories[i]+'StarSpectras.txt','r')
#            for star in foo.readlines():
#                if star.find(grism) != -1 : 
#                    star=star.split()[0]
#                    shutil.copy(MotherDIR+'/'+directories[i]+star,MotherDIR+'/LampRepo/')
#                    Found='yes'
#                    break
#            foo.close()
#            i=i+1
        
        # Running apall
    for lampset in Lamps:
        if not os.path.exists(lampset[-2]) :
            print('Cannot find the Lamp spectra..')
            print('Copy a lamp with following specifications to current directory and enter the lamp img name below.')
            print(lampset)
            Lampimg=raw_input("Enter lamp image name:")
            print('Cannot find the Star spectra..')
            print('Copy a Star with following specifications to current directory and enter the star img name below.')
            print(lampset,Lampimg)
            star=raw_input("Enter star image name:")
        else:
            Lampimg=lampset[-2]
            star=lampset[-1]
            
        iraf.apall(input=star,nfind=1,b_sample=BACKGROUND,background ='fit',weights ='variance',readnoise=READNOISE,gain=EPADU,t_function=TRACEFUNC,t_order=TRACEORDER,t_niterate=1,ylevel=APPERTURE,interactive=VER)       

#        for Lampimg in LampnameArray[grismLIST.index(grism)] :
            # Run apsum
            # Verify the size of lamp is more than that of object's spec position.
        iraf.apsum(input=Lampimg,references=star[:-5],interactive=VER,find='no',recenter='no',resize='no',edit='no',trace='no',fittrace='no',readnoise=READNOISE,gain=EPADU)
        print("Runing identify interactiverly, Carefully label and make sure the RMS of fit is ~0.01 ")
        iraf.identify(images=Lampimg[:-4]+'ms')
        #Create the LampDataBase.txt which contains each line "Lampimage.ms lampname GrismID"
        hdulist=pyfits.open(Lampimg[:-4]+'ms.fits')
        fooLampData.write(Lampimg[:-4]+'ms'+' '+hdulist[0].header.get(LAMPHDR)+' '+hdulist[0].header.get(GRISMHDR)+' \n')
        hdulist.close()
    fooLampData.close()
    os.system('touch CALIBRATED')
    print('Calibration of all lamps over')

def BiasSub_subrout():
    iraf.images(_doprint=0) 
    iraf.imutil(_doprint=0) 
    iraf.immatch(_doprint=0) 
    iraf.cd(MotherDIR)
    try :
        directories=open(MotherDIR+'/directories','r')
    except IOError :
        #Creating a text file containg the directories to visit if it doesn't already exist
        os.system('''cut -d' ' -f 1 Images4Spec.in | awk 'BEGIN{FS="/";OFS="/"}{$NF="" ; print $0}' | sort | uniq > directories ''')
        directories=open(MotherDIR+'/directories','r')
    for direc in directories.readlines():
        direc=direc.rstrip()
        iraf.cd(MotherDIR+'/'+direc)        
        fooStars=open('StarSpectras.txt','r')
        fooLamps=open('LampSpectras.txt','r')
        fooBias=open('BiasImages.txt','r')
        dimlist=[]
        datalines=fooStars.readlines()
        datalines.extend(fooLamps.readlines())
        for starline in datalines:
            starline=starline.rstrip()
            img=starline.split()[0]
            yxdim=pyfits.getdata(img).shape  #The (Ymax,Xmax) of image
            if not yxdim in dimlist : dimlist.append(yxdim)
        BiasArray=[[] for i in range(len(dimlist))]
        for biasline in fooBias.readlines():
            img=biasline.split()[0]
            yxdim=pyfits.getdata(img).shape  #The (Ymax,Xmax) of bias                
            for dimen in dimlist:
                if yxdim[0] < dimen[0] or yxdim[1] < dimen[1] : continue   #Bias smaller than image; Discard
                else :
                    #Slicing the required section from bias frame
                    slicesection=BIASSLICING.replace('imgX',str(dimen[1]))
                    slicesection=slicesection.replace('imgY',str(dimen[0]))
                    slicesection=slicesection.replace('biasX',str(yxdim[1]))
                    slicesection=slicesection.replace('biasY',str(yxdim[0]))
                    iraf.imcopy(input=img+slicesection,output=img+'_'+str(dimen[0])+'_'+str(dimen[1])+'.fits')
                    BiasArray[dimlist.index(dimen)].append(img+'_'+str(dimen[0])+'_'+str(dimen[1])+'.fits') #Adding name in array
        #Now combining the biases by median And appending it to the end of each array
        for i in range(len(BiasArray)) :
            biaslist=BiasArray[i]
            if len(biaslist) > 1 : #Atleast two biases to combine
                foo=open('bias2combine.lst','w')
                for biasimg in biaslist : foo.write(biasimg+' \n')
                foo.close()
                iraf.imcombine(input="@bias2combine.lst", output="Zero_"+str(dimlist[i][0])+"_"+str(dimlist[i][1])+".fits",combine="median")
                BiasArray[i].append("Zero_"+str(dimlist[i][0])+"_"+str(dimlist[i][1])+".fits")
        for starline in datalines :  # Now we will subtract Zero from all objects
            starline=starline.rstrip()
            img=starline.split()[0]
            yxdim=pyfits.getdata(img).shape  #The (Ymax,Xmax) of image
            if len(BiasArray[dimlist.index(yxdim)]) != 0 :
                iraf.imarith(operand1=img, op='-', operand2=BiasArray[dimlist.index(yxdim)][-1], result='zs'+img)
            else : print("No Bias to subtract for "+img)
        fooBias.close()
        fooLamps.close()
        fooStars.close()
        # Updating the StarSpectras.txt and LampSpectras.txt with zs
        os.system("sed -i 's/^/zs/g' StarSpectras.txt")
        os.system("sed -i 's/^/zs/g' LampSpectras.txt")
    print("Bias subtraction over...")    
    directories.close()
    iraf.cd(MotherDIR)        

def Manual_Inspection() :
    """ Opens images one after other to keep or reject """
    ImageLists=[]
    print(" To inspect Bias frames enter 'B' \n To inspect Lamp frames enter 'L' \n To inspect Star frames enter 'S' ")
    print(" Enter the alphabets space seperated. Eg: B L S \n")
    tocheck=raw_input('Enter the list : ')
    tocheck=tocheck.split()
    
    if 'B' in tocheck : ImageLists.append('BiasImages.txt')
    if 'L' in tocheck : ImageLists.append('LampSpectras.txt')
    if 'S' in tocheck : ImageLists.append('StarSpectras.txt')
    
    iraf.cd(MotherDIR)
    try :
        directories=open(MotherDIR+'/directories','r')
    except IOError :
        #Creating a text file containg the directories to visit if it doesn't already exist
        os.system('''cut -d' ' -f 1 Images4Spec.in | awk 'BEGIN{FS="/";OFS="/"}{$NF="" ; print $0}' | sort | uniq > directories ''')
        directories=open(MotherDIR+'/directories','r')
    for direc in directories.readlines():
        direc=direc.rstrip()
        iraf.cd(MotherDIR+'/'+direc)
        print(direc)
        for imagelistsfls in ImageLists :
            foolist=open(imagelistsfls,'r')
            imagenamelines=foolist.readlines()
            foolist.close()
            for line in imagenamelines :
                img=line.split()[0]
                iraf.display(img,1)
                hdulist=pyfits.open(img)
                Comment=hdulist[0].header.get(COMMENTHDR)
                Object=hdulist[0].header.get(OBJECTHDR)
                hdulist.close()
                print(imagelistsfls)
                print(img,Object,Comment)
                verdict=raw_input('Enter "d" to discard :')
                if verdict == 'd' :
                    print("Discarding image "+img)
                    os.system("sed -i '/^"+img+"/d' "+imagelistsfls)
    iraf.cd(MotherDIR)
    directories.close()

def Call_Midas(img,output=None):
    """ Calls Midas to remove cosmic rays. If argument output=output.fits is not given, it will overwite the original """
    if output == None :
        output=img
        if not os.access(img, os.W_OK): os.system('chmod +w '+img)  #Giving write permision to overwright
    #Calculating the median sky value frm center region of image
    hdulist=pyfits.open(img)
    shp= hdulist[0].data.shape
    sky=np.median(hdulist[0].data[shp[0]/4.0:shp[0]*3/4.0,shp[1]/4.0:shp[1]*3/4.0])
    hdulist.close()
    fooMIDAS=open('crremove.prg','w') #MIDAS script
    fooMIDAS.write('indisk/fits '+img+' '+img+'.bdf \n')
    fooMIDAS.write('filter/cosmic '+img+'.bdf Tempimage.bdf '+str(sky)+','+str(EPADU)+','+str(READNOISE)+' \n')
    fooMIDAS.write('outdisk/fits Tempimage.bdf '+output+' \n')
    fooMIDAS.write('bye \n')
    fooMIDAS.close()
    #Now calling midas
    os.system('inmidas -j " @@ crremove "')


def Cosmicrays_subrout() :
    """ Calls inmidas to remove cosmic ray from images """
    ImageLists=['StarSpectras.txt','BiasImages.txt']
    os.chdir(MotherDIR)
    try :
        directories=open(MotherDIR+'/directories','r')
    except IOError :
        #Creating a text file containg the directories to visit if it doesn't already exist
        os.system('''cut -d' ' -f 1 Images4Spec.in | awk 'BEGIN{FS="/";OFS="/"}{$NF="" ; print $0}' | sort | uniq > directories ''')
        directories=open(MotherDIR+'/directories','r')
    for direc in directories.readlines():
        direc=direc.rstrip()
        os.chdir(MotherDIR+'/'+direc)        
        for imagelistsfls in ImageLists :
            foolist=open(imagelistsfls,'r')
            for line in foolist.readlines():
                img=line.split()[0]
                Call_Midas(img)
            foolist.close()
        os.system('rm *.bdf')  # Removing the .bdf files genrated by Midas
    os.chdir(MotherDIR)
    directories.close()

def Createlist_subrout():
    """ Creates the Images4Spec.in containing the image name , grism, exposure time """
    # First creating a file with just the names of images to do photometry.
    os.system("find . -iname '*.fits' > ImageNames.txt")
    os.system("sed '/LampRepo/d' ImageNames.txt | sort > ImageNames.txtT")   #Sorting the image names
    os.system("mv ImageNames.txtT ImageNames.txt")
    # Now opening each image header and creating Images4Photo.in with filter, exposure time, threshold , UT
    foo=open('ImageNames.txt','r')
    fooOUT=open('Images4Spec.in','w')
    fooBias=open('BiasImages.txt','a')     #Just incase you have all file in current directory...
    fooLamp=open('LampSpectras.txt','a')
    fooStar=open('StarSpectras.txt','a')
    LampList=[]

    for img in foo.readlines():
        img=img.rstrip()
        wdir=img.split('/')[-2]
        if wdir != os.getcwd().split('/')[-1] : #If we are not already in img dir
            if not fooBias.closed : fooBias.close()
            if not fooLamp.closed : fooLamp.close()
            if not fooStar.closed : fooStar.close()
            os.chdir(MotherDIR)  #Going back to parent directory
            DIRtogo="/".join(img.split('/')[:-1]) #Now going to dir of img
            os.chdir(DIRtogo)
            fooBias=open('BiasImages.txt','a')
            fooLamp=open('LampSpectras.txt','a')
            fooStar=open('StarSpectras.txt','a')

        try :
            hdulist=pyfits.open(img.split('/')[-1])
        except IOError,e :
            print ('The file seems to be corrept'+ img )
            print(e)
            print('Continuing to next image')
            continue
            
        Exptime=hdulist[0].header.get(EXPTIMEHDR)
        GrismID=hdulist[0].header.get(GRISMHDR)
        UTtime=hdulist[0].header.get(UTHDR)
        Lamp=hdulist[0].header.get(LAMPHDR)
        hdulist.close()
        yxdim=pyfits.getdata(img.split('/')[-1]).shape  #The (Ymax,Xmax) of image
        if Exptime == 0 : # Bias image
            fooBias.write(img.split('/')[-1]+' '+str(yxdim[0])+' '+str(yxdim[1])+' \n')
            continue
        if GrismID =='ACTIVE' : print ('>>>>+++ ALERT : ACTIVE GRISM IN IMG '+img )
        if yxdim[0] > yxdim[1] : 
            DispAxis=2  # Vertical Spectra
            if not yxdim[0] > 2*yxdim[1] : continue   #Not a rectangular spectra 
        else : 
            DispAxis=1    # Horizontal Spectra
            if not yxdim[1] > 2*yxdim[0] : continue   #Not a rectangular spectra 
        if Lamp != 'OFF' :  #Lamp spectra
            fooLamp.write(img.split('/')[-1]+' '+Lamp+' '+str(GrismID)+' '+str(yxdim)+' \n')
            if not Lamp+' '+str(GrismID) in LampList : LampList.append(Lamp+' '+str(GrismID))
            continue
        # Now the surviving image should be an object
        fooStar.write(img.split('/')[-1]+' '+str(GrismID)+' '+str(Exptime)+'  \n')
        fooOUT.write(img+' '+str(GrismID)+' '+str(Exptime)+' '+str(UTtime)+'  \n')
    
    fooOUT.close()
    foo.close()
    if not fooBias.closed : fooBias.close()
    if not fooLamp.closed : fooLamp.close()
    if not fooStar.closed : fooStar.close()
    os.chdir(MotherDIR)
    print("Images4Spec.in file created. Please edit it as required. Tip: Gawk and sed may come to use \n In every directory also created StarSpectras.txt LampSpectras.txt and BiasImages.txt")
    print ("Keep the following Lamp's claibrated spectra ready in LampRepo/")
    print (LampList)
    if not os.path.exists('LampRepo/CALIBRATED') :
        os.system('mkdir -p LampRepo/')
        fooLampRepo=open('LampRepo/Lamps.list','w')
        for lamp in LampList : fooLampRepo.write(lamp+' \n')
        fooLampRepo.close()
        print ('Enter the name of corresponding spectras in the 2nd column of LampRepo/Lamps.list')
        print ('Keep star spectra also of the corresponding lamps. and Enter the name in 3rd column of LampReo/Lamps.list')
    else :
        print('You seems to have already the LampRepo/ Directory with calibrated spectras')
        print('Please very that it includes all the lamps and Grisms printed above')
        
def Backup_subrout():
    """ Copies all the files in present directory to the ../BACKUPDIR """
    os.system('mkdir  ../'+BACKUPDIR)
    print("Copying files to ../"+BACKUPDIR)
    os.system('cp -r * ../'+BACKUPDIR)

#----Main Program Begins here....
configfile=open('Spectroscopy.conf','r')
for con in configfile.readlines():
    con=con.rstrip()
    if len(con.split()) >= 2 :
        if con.split()[0] == "VERBOSE=" :
            VER=con.split()[1]
#        elif con.split()[0] == "THRESHOLD=" :
#            threshold=con.split()[1]
        elif con.split()[0] == "EPADU=" :
            EPADU=con.split()[1]
        elif con.split()[0] == "READNOISE=" :
            READNOISE=con.split()[1]
        elif con.split()[0] == "BIASSLICING=" :
            BIASSLICING=con.split()[1]

        elif con.split()[0] == "APPERTURE=" :
            APPERTURE=con.split()[1]
        elif con.split()[0] == "BACKGROUND=" :
            BACKGROUND=con.split()[1]
        elif con.split()[0] == "TRACEFUNC=" :
            TRACEFUNC=con.split()[1]
        elif con.split()[0] == "TRACEORDER=" :
            TRACEORDER=con.split()[1]
        elif con.split()[0] == "NORMFUNC=" :
            NORMFUNC=con.split()[1]
        elif con.split()[0] == "NORMORDER=" :
            NORMORDER=con.split()[1]
        elif con.split()[0] == "DISPAXIS=" :
            DISPAXIS=con.split()[1]

       
        elif con.split()[0] == "EXPTIME=" :
            EXPTIMEHDR=con.split()[1]
        elif con.split()[0] == "GRISM=" :
            GRISMHDR=con.split()[1]
        elif con.split()[0] == "LAMP=" :
            LAMPHDR=con.split()[1]
        elif con.split()[0] == "UT=" :
            UTHDR=con.split()[1]
        elif con.split()[0] == "OBJECT=" :
            OBJECTHDR=con.split()[1]
        elif con.split()[0] == "COMMENT=" :
            COMMENTHDR=con.split()[1]

        elif con.split()[0] == "OUTPUT=" :
            OUTPUTfile=con.split()[1]
        elif con.split()[0] == "BACKUP=" :
            BACKUPDIR=con.split()[1]
configfile.close()
MotherDIR=os.getcwd()
#    OUTPUTfilePATH=MotherDIR+'/'+OUTPUTfile
parentdir=MotherDIR.split('/')[-1]
print("Very Very Important: Backup your files first.\n")
print(" ---------------- The Spectroscopy Script --------------- \n")
print("Enter the Serial numbers (space seperated if more than one task in succession) \n")
print("0  Backup files in current directory to ../"+BACKUPDIR+"\n")
print("1  Make the list of images, Images4Spec.in to do Spectoscopy \n")
print("2  Remove Cosmic Rays on all the images in Images4Spec.in. IMP:It will OVERWRITE original images.\n")
print("3  Manual inspection of every image, to reject any bad frames. \n")
print("4  Bias subtraction of spectras of each night \n")
print("5  Identify the calibration Lamb Lines in LampRepo/ if calibrated files don't already exist \n")
print("6  Do Spectra Reduction \n")
print("7  Normalise the Spectra Counts \n")
print("8  Do Flux Calibration \n")
print("--------------------------------------------------------------- \n")
todo=raw_input('Enter the list : ')
todo=todo.split()


if  ("3" in todo) or ("4" in todo) or ("5" in todo)or ("6" in todo) or ("7" in todo) :
    from pyraf import iraf
for task in todo :
    if task == "0" :
        Backup_subrout()
    elif task == "1" :
        Createlist_subrout()
    elif task == "2" :
        Cosmicrays_subrout()
    elif task == "3" :
        Manual_Inspection()
    elif task == "4" :
        BiasSub_subrout()
    elif task == "5" :
        Lamp_identify_subrout()
    elif task == "6" : 
        Spectroscopy()
    elif task == "7" : 
        Normalise_Counts()
    elif task == "8" : 
        Flux_Calibration()
    
print("All tasks over....Enjoy!!!")
            
