import paramiko

from datetime import datetime
from io import StringIO
from urllib.request import urlopen
from xml.dom.minidom import parseString
from scp import SCPClient
from vars import ref, update_site_host, update_site_ssh_user, update_site_ssh_key

base_url = f'https://{update_site_host}'

upload_temp_directory='uploads'
target_directory='/sonarsource/var/opt/sonarsource/eclipse-uc.sonarlint.org'

now_as_epoch_millis = str(round(datetime.utcnow().timestamp() * 1000))

# <?xml version="1.0" encoding="UTF-8"?>
# <repository name="&quot;SonarLint for Eclipse Update Site&quot;" type="org.eclipse.equinox.internal.p2.metadata.repository.CompositeMetadataRepository" version="1.0.0">
#   <properties size="1">
#     <property name="p2.timestamp" value="### epoch timestamp millis, must be bumped ###"/>
#   </properties>
#   <children size="### must be incremented ###">
#     <child location="https://binaries.sonarsource.com/SonarLint-for-Eclipse/releases/3.1.0/"/>
#     [...]
#   </children>
# </repository>

def append(version, file_name):
  with urlopen(f'{base_url}/{file_name}') as request:
    content = request.read()
    document = parseString(content)
    document.getElementsByTagName('property')[0].setAttribute('value', now_as_epoch_millis)
    children_node = document.getElementsByTagName('children')[0]
    children_size = int(children_node.getAttribute('size'))
    children_node.setAttribute('size', str(children_size + 1))
    new_child = document.createElement('child')
    new_child.setAttribute('location', f"https://binaries.sonarsource.com/SonarLint-for-Eclipse/releases/{version}/")
    children_node.appendChild(new_child)
    with open(file_name, 'w') as output:
      document.writexml(output, encoding = 'UTF-8')

def exec_ssh_command(ssh_client, command):
  stdin, stdout, stderr = ssh_client.exec_command(command)
  stdout_contents = '\n'.join(stdout.readlines())
  print(f"stdout: {stdout_contents}")
  stderr_contents = '\n'.join(stderr.readlines())
  print(f"stderr: {stderr_contents}")
  if stderr_contents:
    raise Exception(f"Error during the SSH command '{command}': {stderr_contents}")

def upload_to_authorized_location(ssh_client, files_to_upload):
  exec_ssh_command(ssh_client, f"mkdir -p {upload_temp_directory}")
  scp = SCPClient(ssh_client.get_transport())

  for file_to_upload in files_to_upload:
    scp.put(file_to_upload, remote_path=upload_temp_directory)
    print(f'uploaded {file_to_upload} to {upload_temp_directory}')
  scp.close()

def move_files_to_final_destination(ssh_client):
  exec_ssh_command(ssh_client, f"sudo cp {upload_temp_directory}/*.xml {target_directory} && rm -f {upload_temp_directory}/*.xml")
  print(f'files moved to {target_directory}')

def connect_to_update_site():
  ssh_client = paramiko.SSHClient()
  ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  private_ssh_key = paramiko.RSAKey.from_private_key(StringIO(update_site_ssh_key))
  ssh_client.connect(hostname=update_site_host, username=update_site_ssh_user, pkey=private_ssh_key)
  print(f'Connected to {update_site_host}')
  return ssh_client

def upload_updated_files(files_to_update):
  ssh_client = connect_to_update_site()
  upload_to_authorized_location(ssh_client, files_to_update)
  move_files_to_final_destination(ssh_client)

def publish_version_on_p2_update_site():
  # version should have been checked in previous step
  version = ref.replace('refs/tags/', '', 1)

  files_to_update = ['compositeContent.xml', 'compositeArtifacts.xml']

  for file_to_update in files_to_update:
    append(version, file_to_update)
  
  upload_updated_files(files_to_update)

publish_version_on_p2_update_site()