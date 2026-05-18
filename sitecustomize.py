import sys
import types

if 'audioop' not in sys.modules:
    dummy = types.ModuleType('audioop')
    dummy.error = Exception
    dummy.mul = lambda cp, size, factor: b''
    dummy.max = lambda cp, size: 0
    dummy.lin2lin = lambda fragment, width, newwidth: b''
    dummy.ratecv = lambda fragment, width, nchannels, inrate, outrate, state: (b'', None)
    dummy.ulaw2lin = lambda fragment, width: b''
    dummy.lin2ulaw = lambda fragment, width: b''
    sys.modules['audioop'] = dummy
    print("[SYSTEM PATCH] Audioop has been successfully mocked before discord.py check.")
