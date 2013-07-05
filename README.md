piwebcam
========
A simple python script to generate pictures from an attached webcam, save the pictures as files, email the pictures, or upload them to Amazon S3.

### Scope & Purpose
This program is built to work on the Raspberry Pi. The purpose is to take regular 
snapshots from a webcam, and send those pictures to an email recipient, or to 
Amazon S3.

### Dependencies
This program depends on [fswebcam](http://www.firestorm.cx/fswebcam/) which is a neat program that captures a single shot from a webcam and writes it to a file. [fswebcam](http://www.firestorm.cx/fswebcam/) has a lot of settings which can be stored in a config file. I have found that these settings work best on a Microsoft webcam but you should tinker and try out different settings for your webcam. 

#### fswebcam configuration setttings
    device /dev/video0
    resolution 1280x720 
    set brightness=40%
    set contrast=50%
    set "Power Line Frequency"="Disabled"
    set "Sharpness"=100%
    jpeg 79
    palette MJPEG

Put the above settings into a file (I named my file `.fswebcamconf` and put it in my home directory). You then refer to that file in the configuration of this script under `_glob_FSWConfigFile` in the config settings outlined below. This will instruct fswebcam to load those settings each time it is invoked by this script. 

### Configuration
The program is configured via a config file which is sourced by the program from
the same directory from which the program is launched. The config file follows a
JSON syntax, and must include at least these items:

    {
        "email_account" : "an_email@email.com",
        "email_server" : "an_smtp.server.com",
        "email_server_port" : 587,
        "_glob_EmailRecipient" : "wheretosendemail@email.com",
        "_glob_FSWCConfigFile" : "/path/to/.fswebcamconf",
        "_glob_S3BucketName" : "S3_bucket_name",
        "_glob_ImageOutputDirectory" : "/path/to/temp/directory/",
        "_glob_FixedFileName" : "some_file_name.jpg"

    }

While these configuration values are needed, you must also supply some configuration on the command line (these can be moved into the config file eventually but for now this allows flexibilty at the command line). For example you must supply a password for your email account from which you will send emails (password for an account on an smtp server which requires credentials, for example). 

### Command line help
There is command line help which can be invoked by:

    `snap_mail.py -h`

This should show you this output (note: this might change as I tweak this app so always use the output from the app as the latest command line switches):

    usage: ./snap_mail.py [-e -p <gmail_pw> [-r <recipient>]] [-t --timestamp] [-i interval] [-s pathtofile] [-a] [-h --help]
    NOTE: this program depends on .fswebcamconf which is pointed to by config settings.

        -t: create a time-stamped file (will generate a list of files).
            By default this is not set, and images will overwrite a single file. 

        -e: sends an email of the capture file.
            By default, does not send email.

        -a: posts the output to S3
            By default, does not do this.

        -p: <password>: use this password for email send mail account.
            Must be supplied by caller to match email smtp account credentials.

        -i: <interval_seconds>: interval to take snapshots, in seconds. 
            By default, this is set to 60 seconds. 

        -s: <pathtofile>: save the image to the filename provided in pathtofile (uses cp to copy image to a file).
            By default this is disabled. NOTE: this is a filename to store the output file to.

        -r <recipient>: If specified this is the email to which photos will be sent 
            if -e is specified, meaning that email is to be sent.
            The program already uses a temporary image to overwrite on each capture. This filename
            provided with -s can be a filename which another script can call, iterating on filename.

        There are no required parameters needed to run this script.  That is, 
        running this script by itself without any parameters or arguments at the 
        command line will generate an output file that is kept in RAM file system (in the /run/shm 
        directory, and will not email the results or save the file to another permanent location.
        nor post it to AWS S3.


The most basic use of this program is to simply take a periodic snapshot from the webcam and save it to the same file each time. Note that on the Raspberry Pi there is a RAM-disk under /run/shm which is where you can safely store the image, and since it's RAM-based, it does not wear on the SD card's flash, which has a limited write lifespan.  This was done intentionally so if you wish you can change where you store the output file from the webcam snapshot. 

### What This Runs On
This program was tested on Raspberry Pi model B, using Microsoft webcams.  I have not attempted to run it on any other Linux machines but I imagine it 'should just work' if you have fswebcam on the distro. 

### TODO
1. DOC BUG: Document the rest of the functionality around file saving
1. CODE BUG: Update the password to not be a commandline parameter and instead ask the user for it interactively so it never is shown even as a commandline parameter
1. DOC BUG: explain how the S3 configuration works (boto, and where it gets its config, how to set up boto, etc.)
1. DOC BUG: explain the most common use cases
1. DOC BUG: explain how to run this in the background on Pi, using `disown %1`
