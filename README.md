# cronup
Upgrade your cron jobs with a wrapper that gives you better insight into
how your jobs are doing. The script hostname, stdout/stderr, duration, user, 
command, exit code are all logged from the script your ran.


## Requirements
- nix
- python2.7

## Usage
```shell
./cronup.py -c /home/cats/backup.sh
./cronup.py -i cleaner -c 'ls /tmp/stale' -t "30s" 
./cronup.py -i loud-cleaner -c 'ls /tmp/stale' -v
```

## Test
```shell
cd ./test
python suite.py
```

### Todo
- Installer
- Track mail logs for cron in /var/mail/$user, /var/spool/mail/$user
- Web server that logs can be posted to for log centralization
