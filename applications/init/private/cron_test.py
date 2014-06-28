import psutil
import sys
import subprocess
import UUID
if not "python" in [proc.name() for proc in psutil.process_iter()]:
	subprocess.call("~/biddrive.com/start_service.sh", shell=True) #http://goo.gl/X3LSGD
	
"""
In start_service.sh
nohup python web2py.py -K init -X -p 8889 -i 127.0.0.1 -a 9ieXej92kef
"""