"""
Sample Ruby OS script - System Status Summary
"""
import psutil
import datetime

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cpu_pct = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('C:\\')
    
    print(f"System Health Check [{now}]")
    print(f"- CPU Usage:    {cpu_pct}%")
    print(f"- RAM Usage:    {mem.percent}% (Used {round(mem.used/(1024**3), 1)}GB / {round(mem.total/(1024**3), 1)}GB)")
    print(f"- C: Drive:     {disk.percent}% used ({round(disk.free/(1024**3), 1)}GB free)")

if __name__ == "__main__":
    main()
