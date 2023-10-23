import subprocess
import os

año=2023
mes=9
dia=21
h_at=0
m=0

for i in range(1111111):
    # h_at=i
    # m=i
    # command = f"at {h_at:02d}:{m:02d} {dia:02d}.{mes:02d}.{str(año)[-2:]} -f dummy.py " + "2>&1 | awk '/job/ {print $2}'"
    # output = subprocess.check_output(command, shell=True).decode().strip()
    # print("Command: ",command)
    # print("--Scheduled task ID:", output)
    # print('\n') 
    
    
    try:
        command = f'atrm {i+1}'
        print(command)
        output = subprocess.check_output(command, shell=True)
    except:
        pass
    pass

# command = "at 11:20 11 July 2023 -f /home/usuario/Escritorio/ai2app-backend/dummy_print.py 222 2>&1 | awk 'END{print $2}'"
# output = subprocess.check_output(command, shell=True).decode().strip()

# print(f"Command: {command}")
# print(f"--Scheduled task ID: {output}")
