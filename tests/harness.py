"""Offline harness: stub genlayer runtime, load SkillBond.py, drive it.

Mirrors the Heirloom tests-v2 harness. WEB values are raw bytes (served with
status 200) or (status, bytes) tuples. The chain model in call(): the sent
value lands in the contract balance first and stays there even when the call
reverts (runner behaviour); transfers emitted during a call leave the balance
immediately (a "landed" emission). Tests model an in-flight / stranded
emission by adding the amount back to the balance (funds never left).
"""
import sys, types, json, hashlib

TRANSFERS = []          # (recipient, amount) emitted via _Recipient.emit_transfer
WEB = {}                # url -> bytes | (status, bytes); missing key = fetch failure
PROMPT_FN = None        # callable(prompt, images) -> jury verdict stub
CLOCK = {"iso": "2026-11-20T00:00:00"}

class UserError(Exception):
    pass

class _Msg:
    sender_address = "0x" + "a" * 40
    value = 0
    @property
    def datetime(self):
        return CLOCK["iso"]

class _Resp:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status

class _Web:
    @staticmethod
    def get(url):
        if url not in WEB:
            raise Exception("unreachable: " + str(url))
        v = WEB[url]
        if isinstance(v, tuple):
            return _Resp(v[1], v[0])
        return _Resp(v, 200)

class _Nondet:
    web = _Web()
    @staticmethod
    def exec_prompt(prompt, response_format=None, images=None):
        assert PROMPT_FN is not None, "no jury stub set"
        return PROMPT_FN(prompt, images)

class _Eq:
    @staticmethod
    def strict_eq(fn):
        return fn()

class _Public:
    def write(self, fn):
        return fn
    write.payable = staticmethod(lambda fn: fn)
    def view(self, fn):
        return fn

class _Recipient:
    def __init__(self, addr):
        self.addr = str(addr)
    def emit_transfer(self, value=None):
        TRANSFERS.append((self.addr, int(value)))

def _contract_interface(cls):
    return _Recipient

class _Contract:
    balance = 0

gl = types.ModuleType("genlayer")
gl.contract = types.SimpleNamespace(Contract=_Contract)
gl.public = _Public()
gl.vm = types.SimpleNamespace(UserError=UserError)
gl.message = _Msg()
gl.nondet = _Nondet()
gl.eq_principle = _Eq()
gl.evm = types.SimpleNamespace(contract_interface=_contract_interface)
storage = types.ModuleType("genlayer.storage")
class TreeMap(dict):
    pass
storage.TreeMap = TreeMap
gtypes = types.ModuleType("genlayer.types")
gtypes.Address = lambda a: str(a)
gtypes.u256 = int
gtypes.bigint = int
sys.modules["genlayer"] = gl
sys.modules["genlayer.storage"] = storage
sys.modules["genlayer.types"] = gtypes

SRC = open("/home/hatch/workspace/skillbond/SkillBond.py").read()
ns = {}
exec(compile(SRC, "SkillBond.py", "exec"), ns)
SkillBond = ns["SkillBond"]

A = "0xd2af69bb67d446526661a80a280820599c601ed3"   # contract admin (deployer)
P = "0x0bba411375d7074178980e610b5311dd6ed34d74"   # promiser 1
Q = "0x6fa23bd191266a8680c195ec6a618d2d9d584cab"   # promiser 2 / outsider
TREASURY = "0x" + "9" * 40
OUT = "0x" + "1" * 40                              # unrelated outsider
DAY = 86400

def set_time(unix):
    import datetime as _dt
    CLOCK["iso"] = _dt.datetime.utcfromtimestamp(unix).strftime("%Y-%m-%dT%H:%M:%S")

def now_unix():
    import calendar as _cal
    s = CLOCK["iso"]
    return _cal.timegm((int(s[0:4]), int(s[5:7]), int(s[8:10]), int(s[11:13]), int(s[14:16]), int(s[17:19])))

def fresh(balance=0, treasury=TREASURY):
    gl.message.sender_address = A
    TRANSFERS.clear()
    WEB.clear()
    globals()["PROMPT_FN"] = None
    c = SkillBond.__new__(SkillBond)
    c.bonds = TreeMap(); c.reps = TreeMap(); c.claimable = TreeMap(); c.pendings = TreeMap(); c.pstamps = TreeMap()
    SkillBond.__init__(c, treasury)
    c.balance = balance
    return c

def call(c, sender, fn, *args, value=0):
    """Run one top-level call the way the chain would: value lands first,
    transfers emitted during the call leave the contract balance."""
    gl.message.sender_address = sender
    gl.message.value = value
    if value:
        c.balance += value
    before = len(TRANSFERS)
    try:
        out = fn(*args)
    finally:
        for (_r, amt) in TRANSFERS[before:]:
            c.balance -= amt
    return out

def accounted(c):
    return int(c.lockw) + int(c.bondw) + int(c.poolw) + int(c.tcw) + int(c.tpw)

def _snap(c):
    return (json.dumps({k: v for k, v in c.bonds.items()}, sort_keys=True),
            json.dumps({k: v for k, v in c.reps.items()}, sort_keys=True),
            json.dumps({k: v for k, v in c.claimable.items()}, sort_keys=True),
            json.dumps({k: v for k, v in c.pendings.items()}, sort_keys=True),
            json.dumps({k: v for k, v in c.pstamps.items()}, sort_keys=True),
            c.own, c.pown, int(c.nb), int(c.lockw), int(c.bondw), int(c.poolw),
            int(c.tcw), int(c.tpw), int(c.wo), int(c.pool_in), int(c.pool_out),
            int(c.total_slashed), int(c.bonds_met), int(c.bonds_slashed),
            len(TRANSFERS))

def expect_err(c, sender, fn, *args, code, value=0):
    snap = _snap(c)
    try:
        call(c, sender, fn, *args, value=value)
    except UserError as e:
        assert str(e) == code, f"expected {code}, got {e}"
        # NOTE: harness cannot roll back in-place dict edits on raise; the
        # contract only mutates after all gates pass, so snapshots must match.
        assert _snap(c) == snap, f"state changed on {code}"
        return
    raise AssertionError(f"expected UserError {code}, call succeeded")

def conserve(c, excess=0):
    got = int(c.balance) - accounted(c)
    assert got == excess, f"conservation broken: balance-accounted={got} expected excess={excess} " \
        f"(bal={c.balance} lock={c.lockw} bond={c.bondw} pool={c.poolw} tcw={c.tcw} tpw={c.tpw})"

def sha(b):
    return hashlib.sha256(b).hexdigest()
