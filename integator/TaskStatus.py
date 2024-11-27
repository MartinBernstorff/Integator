class Commit:
   hash: str
   timestamp: dt.datetime
   author: str
   tasks: List[TaskStatus]

class TaskStatus:
   name: str
   command: str
   status: EnumStatus
   duration: dt.timedelta
    
# DTO to handle the empty note. Only parse the TaskStatus' if they exist.