import tarfile
import boto3
import sys
import os
import commentjson
import requests
import glob
from datetime import datetime, timezone, timedelta

def log(message):
    ''' Print sync output to a Discord channel so we always know what's going on
    '''
    print(message)
    # source: https://makerhacks.com/python-messages-discord/	
    webhook_url = "https://discordapp.com/api/webhooks/605821430524805122/XyLcccGOgKmEaNmzO1vAS-dgSVHj1H6FoYzx8pLgsAN64BncqAdpVi14jm76XoaNgRpZ"
    r = requests.post(webhook_url, data = {"content": message})
    
def mount_backup(key, config):
    ''' Print the CLI flag required to mount the given backup directory to the server's Docker instance
    '''

    # The json key "host-dir" is relative to the working directory by default
    host_dir = config['host-dir']
    if host_dir[0] in '~/':
        host_dir=os.path.expanduser(host_dir)
    else:
        host_dir='{}/{}'.format(os.getcwd(), host_dir)

    # Create the directory if it doesn't exist
    if not os.path.exists(host_dir):
        os.makedirs(host_dir)
        
    # The json key "container-dir" is always absolute, but doesn't share the same home dir
    container_dir = config['container-dir']

    mount_enclosing_dir = 'mount-enclosing-dir' not in config or config['mount-enclosing-dir'] == True

    sources=[host_dir]
    targets=[container_dir]
    if not mount_enclosing_dir:
        sources = [dir[:-1] for dir in glob.glob("{}/**/".format(host_dir))]
        targets = ['{}{}'.format(container_dir, source[source.rfind('/')+1:]) for source in sources]

        # Create the manifest inside the container for uploading child directories together to S3 later
        manifest_path='{}.json'.format(key)
        with open(manifest_path, 'w') as manifest:
            commentjson.dump(targets, manifest)
        sources.append('{}/{}'.format(os.getcwd(), manifest_path))
        targets.append('/{}'.format(manifest_path))

    for i in range(len(sources)):
        print(' --mount type=bind,source={},target={}'.format(sources[i], targets[i]))
	
def upload_backup(key, config, bucket_name):
    ''' Generate a tar file for the given backup directory and upload it
    '''

    if 's3-upload' not in config or config['s3-upload'] == 'never':
        # log("{} never uploads a backup".format(key))
        return
    
    archive_path = '{}.tar.gz'.format(key)

    # Check if long enough has passed to re-upload this file
    last_modified = datetime.min.replace(tzinfo=timezone.utc)
    if archive_path in last_modified_times:
        last_modified = last_modified_times[archive_path]

    elapsed_time = datetime.now().replace(tzinfo=timezone.utc) - last_modified
    upload_interval = config['s3-upload']
    days=0
    hours=0
    minutes=0

    index = upload_interval.find('d')
    if index != -1:
        days = int(upload_interval[:index])
        upload_interval= upload_interval[index+1:]
    
    index = upload_interval.find('h')
    if index != -1:
        hours = int(upload_interval[:index])
        upload_interval= upload_interval[index+1:]

    index = upload_interval.find('m')
    if index != -1:
        minutes = int(upload_interval[:index])
        upload_interval= upload_interval[index+1:]

    if elapsed_time < timedelta(days=days, hours=hours, minutes=minutes):
        # log("It isn't time to upload a backup for {}".format(key))
        return
    else:
        log('uploading a new backup for {} to bucket {}. Last upload was {}'.format(key, bucket_name, last_modified))
        
    with tarfile.open(archive_path, 'w:gz') as upload_file:
        container_dir = config['container-dir']

        mount_enclosing_dir = 'mount-enclosing-dir' not in config or config['mount-enclosing-dir'] == True

        targets=[]
        if not mount_enclosing_dir:
            manifest_path='/{}.json'.format(key)
            with open(manifest_path, 'r') as manifest:
                targets = commentjson.load(manifest)
        else:
            # if the container dir is not fully specified, fill it out
            if container_dir[-1] == '/':
                host_dir = config['host-dir']
                last_slash_idx = host_dir.rfind('/')
                container_dir += host_dir[last_slash_idx+1:]
            targets=[container_dir]
        for target in targets:
            upload_file.add(target)
            log('adding {} to archive'.format(target))

    log('Uploading {} as archive {} to S3 key {}'.format(container_dir, archive_path, bucket_name))
    s3.upload_file(archive_path, bucket_name, archive_path)

def download_backup(key, config, bucket_name):
    ''' Download a tar file for the given backup directory and unzip it where it belongs
    '''

#       s3.download_file('minerl-server-backup', 'synced-worlds.tar', './synced-worlds.tar')
#        s3.download_file('minerl-server-backup', 'playerdata.tar', './playerdata.tar')
# with open('./synced-worlds.tar', 'rb') as download_file:
#            tar = tarfile.TarFile(fileobj=download_file, mode='r:gz')
#            tar.extractall()
            
#            tar.close()

#        with open('./playerdata.tar', 'rb') as download_file:
#            tar = tarfile.TarFile(fileobj=download_file, mode='r:gz')
#            tar.extractall()
            
#            tar.close()

#        os.remove('./synced-worlds.tar')
#        os.remove('./playerdata.tar')

    
    pass

bucket_name=''
s3=None
bucket=None
last_modified_times={}
if __name__ == "__main__":
    try:
        # Load the file that defines bind mounts and s3 sync behavior
        sync_config=None
        with open('./sync-config.json', 'r') as f:
            sync_config = commentjson.load(f)

        # mount is not like the other 2 commands. it just prints bash arguments
        if sys.argv[1] == 'mount':
            for backup_file in sync_config.keys():
                mount_backup(backup_file, sync_config[backup_file])
            exit()
            
            
        # Sync dev instance files to a different s3 file prefix to avoid mixing them up
        bucket_name = 'minerl-server-backup'
        if 'MODE' not in os.environ or os.environ['MODE'] == 'dev':
            bucket_name += '-dev' 
   
        # log('----------------------------------------------------')
        # log('world-sync.py *{}* called at {} for prefix {}'.format(sys.argv[1], str(datetime.now()), bucket_name))
            
        ############### TESTING

        #mount_backup('persistent-worlds', sync_config['persistent-worlds'])
        #mount_backup('herobraine-playerdata', sync_config['herobraine-playerdata'])
        #mount_backup('aws-creds', sync_config['aws-creds'])
        # upload_backup('persistent-worlds', sync_config['persistent-worlds'])
        # upload_backup('herobraine-playerdata', sync_config['herobraine-playerdata'])

        #exit()

        ############### END TESTING    

        s3 = boto3.client('s3')
        s3_r = boto3.resource('s3')
        bucket = s3_r.Bucket(bucket_name)

        # Calculate last modified times
        for key in bucket.objects.all():
            last_modified_times[key.key] = key.last_modified
        
        for backup_file in sync_config.keys():
            if sys.argv[1] == "up":
                upload_backup(backup_file, sync_config[backup_file], bucket_name)
            elif sys.argv[1] == "down":
                download_backup(backup_file, sync_config[backup_file], bucket_name)
            else:
                log('Error: worldsync script must be called with a valid subcommand')
                
    except Exception as e:
        log('Error during backup for bucket {}: {}'.format(bucket_name, str(e)))

