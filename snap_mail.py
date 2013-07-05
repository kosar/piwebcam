#!/usr/bin/python
import os
import sys
import getopt
import smtplib
import subprocess
import datetime 
import socket
import json
from time import sleep
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_PARAMS = {
    'email_account':'',
    'email_server':'',
    'email_server_port':587
}

_glob_ImageOutputDirectory=''
_glob_S3BucketName=''
_glob_FSWCConfigFile = ''
_glob_FixedFileName='output.jpg'
_glob_pw = ''
_glob_TimeStampFiles = False
_glob_EmailImage = False
_glob_interval = 60
_globPathToSaveFileTo = ''
_glob_SaveImage = False
_glob_EmailRecipient = ''
_glob_PostToS3 = False


def usage(arg0):
    print 'usage: %s [-e -p <gmail_pw> [-r <recipient>]] [-t --timestamp] [-i interval] [-s pathtofile] [-a] [-h --help]' % arg0
    print '\
NOTE: this program depends on .fswebcamconf which is pointed to in config settings.\n\
\n\t-t: create a time-stamped file (will generate a list of files).\
\n\t\tBy default this is not set, and images will overwrite a single file. \
\
\n\n\t-e: sends an email of the capture file.\
\n\t\tBy default, does not send email.\
\
\n\n\t-a: posts the output to S3\
\n\t\tBy default, does not do this.\
\
\n\n\t-p: <password>: use this password for email send mail account.\
\n\t\tMust be supplied by caller to match email smtp account credentials.\
\
\n\n\t-i: <interval_seconds>: interval to take snapshots, in seconds. \
\n\t\tBy default, this is set to 60 seconds. \
\n\n\t-s: <pathtofile>: save the image to the filename provided in pathtofile (uses cp to copy image to a file).\
\n\t\tBy default this is disabled. NOTE: this is a filename to store the output file to.\
\n\n\t-r <recipient>: If specified this is the email to which photos will be sent \
\n\t\tif -e is specified, meaning that email is to be sent.\
\n\t\tThe program already uses a temporary image to overwrite on each capture. This filename\
\n\t\tprovided with -s can be a filename which another script can call, iterating on filename.\
\n\n\tThere are no required parameters needed to run this script.  That is, \
\n\trunning this script by itself without any parameters or arguments at the \
\n\tcommand line will generate an output file that is kept in RAM file system (in the /run/shm \
\n\tdirectory, and will not email the results or save the file to another permanent location.\
\n\tnor post it to AWS S3.\
'

def printFlags():
    print 'flags: '
    print 'TimeStamp files: ' + str(_glob_TimeStampFiles)
    print 'Email images: ' + str(_glob_EmailImage)
    print 'Interval: ' + str(_glob_interval)
    if _glob_TimeStampFiles == False:
        print 'Fixed file name: ' + _glob_FixedFileName
    print 'FSWConfigFile: ' + _glob_FSWCConfigFile
    print 'Email Params: '
    print EMAIL_PARAMS
    print 'IMAGE Output Directory (temp file): ', _glob_ImageOutputDirectory
    print 'Save Image: ' + str(_glob_SaveImage)
    print 'saveImageToFile: ' + str(_globPathToSaveFileTo)
    print 'Email Recipient: ' + str(_glob_EmailRecipient)
    print 'PostToAWSS3: ' + str(_glob_PostToS3)

def getFlags(argv):
    global _glob_pw
    global _glob_TimeStampFiles
    global _glob_EmailImage
    global _glob_interval
    global _glob_SaveImage
    global _globPathToSaveFileTo
    global _glob_EmailRecipient
    global _glob_PostToS3
    global _glob_ImageOutputDirectory
    global _glob_S3BucketName
    global _glob_FSWCConfigFile
    global _glob_FixedFileName

    try:
        fp=open('config')
        config = json.load(fp)
        EMAIL_PARAMS['email_account']=config['email_account']
        EMAIL_PARAMS['email_server']=config['email_server']
        EMAIL_PARAMS['email_server_port']=config['email_server_port']
        _glob_S3BucketName = config['_glob_S3BucketName']
        _glob_EmailRecipient = config['_glob_EmailRecipient']
        _glob_ImageOutputDirectory = config['_glob_ImageOutputDirectory']
        _glob_FSWCConfigFile =  config['_glob_FSWCConfigFile']
        _glob_FixedFileName = config['_glob_FixedFileName']

    except Exception:
        print 'Exception caught setting up configs...exiting'
        print 'Ensure there is a config file, usually named config, in the same directory as this script.'
        print 'Sample config:'
        print '''{\
\t\t    "email_account" : "someone@gmail.com",
\t\t    "email_server" : "smtp.gmail.com",
\t\t    "email_server_port" : 587,
\t\t    "_glob_EmailRecipient" : "recipient`@gmail.com",
\t\t    "_glob_FSWCConfigFile" : "/home/my_username/.fswebcamconf",
\t\t    "_glob_S3BucketName" : "photo-bucket",
\t\t    "_glob_ImageOutputDirectory" : "/run/shm"
}
'''
        print (sys.exc_info()[0])
        sys.exit(2)

    try:
        opts, args = getopt.getopt(argv, "p:tehi:s:r:a", ["password=","timestamp","emailimage","help","interval=","saveImageToFile=","emailRecipient=","postToAwsS3"])

    except getopt.GetoptError, err:
        print str(err)
        usage(sys.argv[0])
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-p', '--password'):
            _glob_pw = arg
        elif opt in ('-t', '--timestamp'):
            _glob_TimeStampFiles = True
        elif opt in ('-e', '--emailimage'):
            _glob_EmailImage = True
        elif opt in ('-i', '--interval'):
            _glob_interval = float(arg)
        elif opt in ('-s', '--saveImageToFile'):
            _glob_SaveImage = True
            _globPathToSaveFileTo = arg
        elif opt in ('-a', '--postToAwsS3'):
            _glob_PostToS3 = True
        elif opt in ('-r', '--emailRecipient'):
            _glob_EmailRecipient = arg
        elif opt in ('-h', '--help'):
            usage(sys.argv[0])
            sys.exit(0)


def snapImage(config_file,flagTimeStampedFileName,fixedFileName):
    if flagTimeStampedFileName:
        todays_date = datetime.datetime.today()
        image_name = todays_date.strftime('%m-%d-%y-%H%M%S')
        image_path = _glob_ImageOutputDirectory + image_name + '.jpg'
    else:
        image_path = _glob_ImageOutputDirectory + fixedFileName
        image_name = ''

    grab_cam = subprocess.Popen(("sudo fswebcam -c %s %s" % (config_file,image_path)), shell=True,\
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (std_out, std_err) = grab_cam.communicate()
    return (image_name, image_path, std_out, std_err)


def emailImage(email_params, password, recipient, subject, messagePreamble, filePictureFile, textBody):
    sender = email_params['email_account']
    smtp_server = email_params['email_server']
    smtp_port = email_params['email_server_port']
    # Create the container (outer) email message.
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    msg.preamble = messagePreamble

    # Add in the body
    if (textBody):
        body = MIMEMultipart('alternative') 
        body.attach(MIMEText(textBody, 'plain')) 
        msg.attach(body) 

    # Open the files in binary mode.  Let the MIMEImage class automatically
    # guess the specific image type.
    fp = open(filePictureFile, 'rb')
    img = MIMEImage(fp.read())
    fp.close()

    msg.attach(img)

    if msg:
        session = smtplib.SMTP(smtp_server, smtp_port)
        session.ehlo()
        session.starttls()
        session.ehlo
        session.login(sender, password)
        
        retry_attempts = 3
        while retry_attempts > 0:
            try:
                session.sendmail(sender, recipient, msg.as_string())
                print 'email sent: ' + str(datetime.datetime.today())
                retry_attempts = 0
            except Exception, err:
                print 'Unable to send email (caught exception)...'
                print (err)
                retry_attempts -= 1

        session.quit()


def copyFile(pathFileToSaveFrom, pathFileToSaveTo):
    cp_file = subprocess.Popen(("sudo cp %s %s" % (pathFileToSaveFrom, pathFileToSaveTo)), shell=True)
    cp_file.wait()


def write_file_to_S3 (file_name, file_path, host_name, decorator_metadata):
  #print 'file_name: %s  file_path: %s' % (file_name, file_path)
  try:
    import boto
    conn = None
    bucket = None
    k = None

    if os.path.isfile('%s%s'% (file_path,file_name)):
        file_object=open('%s%s'%(file_path, file_name))
    else: 
        #print 'No such file %s%s' % (file_path, file_name)
        return

    # connect to S3
    conn = boto.connect_s3()

    if (not conn):
        #print 'No connection to S3...aborting.'
        return

    #print 'Getting the bucket %s' % _glob_S3BucketName

    # Get the bucket (TODO: make a parameter)
    bucket = conn.get_bucket(_glob_S3BucketName)

    if bucket:
        #print 'Got bucket...'

        fn = '%s%s' % (file_path, file_name)
        file_key = '%s-%s' % (host_name, decorator_metadata)
        #print 'fn: %s file_key: %s ' % (fn, file_key)

        # Try to get the key if it exists (returns None if doesn't exist)
        k = bucket.get_key(file_key)

        # Create a new key if we didn't get one
        if (not k):
            #print 'No key there, creating key %s' % file_key
            k = bucket.new_key(file_key)

        if not k:
            return

        #print 'Setting contents from file %s' % fn
        k.set_contents_from_file(file_object)

        # make it public (URL: http://s3.amazonaws.com/bucket_name/key)
        #print 'Making public...'
        k.make_public()

    else:
        print '...oops, couldn\'t connect to bucket'

  except Exception:
    #print 'Exception caught...'
    #print (sys.exc_info()[0])
    pass

def main(argv):

    getFlags(argv)
    printFlags()

    this_host_name = 'generic-host'
    try:
        this_host_name=socket.gethostname();
    except:
        pass

    start_time=5
    print ('Starting up in 5 seconds, hit ctrl-c to stop...')
    while start_time>0:
        sleep(1)
        print str(start_time) + '...'
        start_time -= 1

    while True:
        # Take a picture
        image_name,image_path, std_out, std_err = snapImage(_glob_FSWCConfigFile, _glob_TimeStampFiles, _glob_FixedFileName)
        print ('snap!')

        # Send an email if requested
        if _glob_EmailImage:
            todays_date = datetime.datetime.today()
            date_time_stamp = todays_date.strftime('%m-%d-%y-%H%M%S')
            emailImage( EMAIL_PARAMS,
                        _glob_pw,
                        _glob_EmailRecipient, 
                        'Snap %s' % date_time_stamp ,
                        'image name: %s' % image_path,
                        image_path,
                        'snapImage log: %s \n%s\n' % (std_out, std_err))

        # Save the file if requested
        if _glob_SaveImage:
            copyFile( image_path, _globPathToSaveFileTo )

        if _glob_PostToS3:
            write_file_to_S3(_glob_FixedFileName, _glob_ImageOutputDirectory, this_host_name, 'latest')
            try:
                sleep(5) # Sleep to leave the file there so watchers can detect it is there
                # Delete the temporary file created
                os.remove('%s%s' % (_glob_ImageOutputDirectory, _glob_FixedFileName))
                if os.path.isfile('%s%s' % (_glob_ImageOutputDirectory, _glob_FixedFileName)):
                    sleep(10)
                    os.remove('%s%s' % (_glob_ImageOutputDirectory, _glob_FixedFileName))
            except Exception:
                pass

#        # Show progress @ stdout
#        for i in xrange(10):
#            sys.stdout.write('%s\r' % (10-i))
#            sys.stdout.flush()

        sleep(_glob_interval)

if __name__ == "__main__":
    main(sys.argv[1:])
