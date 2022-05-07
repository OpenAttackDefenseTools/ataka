
from ataka.ctfcode.ctf import CTF

import os
import time

ctf = CTF(os.environ["CTF"])

print(ctf.get_round_time())

time.sleep(5)
ctf.reload()
print(ctf.get_round_time())
