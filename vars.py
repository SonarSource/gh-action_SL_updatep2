import os

ref = os.environ.get('GITHUB_REF', 'no github repo in env')

update_site_host=os.environ.get('UPDATE_SITE_HOST','no update site ssh user in env')
update_site_ssh_user=os.environ.get('UPDATE_SITE_SSH_USER','no update site ssh user in env')
update_site_ssh_key=os.environ.get('UPDATE_SITE_SSH_KEY','no update site ssh key in env')
