import random
import string
from datetime import datetime

ALNUM = string.ascii_uppercase + string.digits

def generate_order_id(prefix="ORD"):
    ts = datetime.utcnow().strftime("%m%d%H%M%S")  # 10 chars
    rand = "".join(random.choices(ALNUM, k=6))
    base = f"{prefix}{ts}{rand}"  # may be >20
    # Return last 20 alnum chars (bank requires <21)
    return base[-20:]
