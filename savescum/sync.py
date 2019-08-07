import tarfile
import boto3
import os
import commentjson
import requests
import glob
from datetime import datetime, timezone, timedelta
from savescum.logs import log
from savescum import config

def resolve_host_dir(directory):
    if directory[0] in '~/':
        return os.path.expanduser(host_dir)
    else:
        return '{}/{}'.format(os.getcwd(), host_dir)


def mount_backup(key, config):
    ''' Print the `docker run` CLI flag required to mount the given backup directory to a docker instance
    '''

    # The json key "host-dir" is relative to the working directory by default
    host_dir = config['host-dir']
    host_dir = resolve_host_dir(host_dir)

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

def most_recent_change(directory):
    max_mtime = 0
    for dirname,subdirs,files in os.walk(directory):
        for fname in files:
            full_path = os.path.join(dirname, fname)
            mtime = os.path.mtime(full_path)
            if mtime > max_mtime:
                max_mtime = mtime
                max_dir = dirname
                max_file = fname
    return datetime.fromtimestamp(max_mtime)
                        

def upload_backup(key, json, last_modified_times, s3, bucket_name):
    ''' Generate a `.tar.gz` file for the given backup directory and upload it
    '''

    if 's3-upload' not in json or json['s3-upload'] == 'never':
        # log("{} never uploads a backup".format(key))
        return
    
    archive_path = '{}.tar.gz'.format(key)

    # Check if long enough has passed to re-upload this file
    last_modified = datetime.min.replace(tzinfo=timezone.utc)
    if archive_path in last_modified_times:
        last_modified = last_modified_times[archive_path]

            
    elapsed_time = datetime.now().replace(tzinfo=timezone.utc) - last_modified
    upload_interval = json['s3-upload']

    # TODO use most_recent_change on either the host-dir or container-dir as the case may be    
    # if json['s3-upload'] == 'on-change':
    #    last_local_change = most_recent_change(
    if json['s3-upload'] == 'on-change':
        upload_interval = "1m"
    
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
        in_container='container-dir' in json
        # Quick-and-dirty check for whether we're in a container or not:
        if os.path.exists(json['host-dir']):
            in_container=False

        targets=[os.path.expanduser(json['host-dir'])]
        if in_container:
            container_dir = json['container-dir']

            mount_enclosing_dir = 'mount-enclosing-dir' not in json or json['mount-enclosing-dir'] == True

        
            if not mount_enclosing_dir:
                manifest_path='/{}.json'.format(key)
                with open(manifest_path, 'r') as manifest:
                    targets = commentjson.load(manifest)
            else:
                # if the container dir is not fully specified, fill it out
                if container_dir[-1] == '/':
                    host_dir = json['host-dir']
                    last_slash_idx = host_dir.rfind('/')
                    container_dir += host_dir[last_slash_idx+1:]
                targets=[container_dir]

        for target in targets:
            upload_file.add(target)
            log('adding {} to archive'.format(target))

    log('Uploading target {} as archive {} to S3 key {}'.format(key, archive_path, bucket_name))
    s3.upload_file(archive_path, bucket_name, archive_path)

def download_backup(key, json, bucket_name):
    ''' Download a tar file for the given backup directory and unzip it where it belongs
    '''

#       s3.download_file('{bucket}', '{file}.tar.gz', './{local-file}..tar.gz

# with open('{local-file}.tar.gz', 'rb') as download_file:
#            tar = tarfile.TarFile(fileobj=download_file, mode='r:gz')
#            tar.extractall()

# TODO put it where it belongs
#            tar.close()

#        os.remove('./{local-file}.tar.gz')


    
    pass

def sync_all_targets(command):
    ''' Command must be 'up', 'down', or 'mount'
    '''
    try:
        # Load the file that defines bind mounts and s3 sync behavior
        sync_json=config.json()['targets']
       
        # mount is not like the other 2 commands. it just prints bash arguments
        if command == 'mount':
            for backup_file in sync_json.keys():
                mount_backup(backup_file, sync_json[backup_file])
            exit()
            
            
        bucket_name = config.json()['storage']['s3']['bucket']
   
        s3 = boto3.client('s3')
        s3_r = boto3.resource('s3')
        bucket = s3_r.Bucket(bucket_name)

        # Calculate last modified times
        last_modified_times={}
        for key in bucket.objects.all():
            last_modified_times[key.key] = key.last_modified
        
        for backup_file in sync_json.keys():
            if command == "up":
                upload_backup(backup_file, sync_json[backup_file], last_modified_times, s3, bucket_name)
            elif command == "down":
                download_backup(backup_file, sync_json[backup_file], bucket_name)
            else:
                log('Error: worldsync script must be called with a valid subcommand')
                
    except Exception as e:
        log('Error during backup for bucket {}: {}'.format(bucket_name, str(e)))

