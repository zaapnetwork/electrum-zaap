"""zaap masternode support."""
import time
import base64

import bitcoin
from bitcoin import hash_encode, hash_decode
from transaction import BCDataStream, parse_input
import util

class NetworkAddress(object):
    """A network address."""
    def __init__(self, ip='', port=0):
        self.ip = ip
        self.port = port

    @classmethod
    def deserialize(cls, vds):
        # IPv4-mapped IPv6 address.
        _ = vds.read_bytes(12);
        ip = []
        for i in range(4):
            ip.append(vds.read_uchar())
        ip = '.'.join(map(str, ip))
        # Ports are encoded as big-endian.
        port = vds._read_num('>H')
        return cls(ip=ip, port=port)

    @classmethod
    def from_dict(cls, d):
        kwargs = {}
        for key in ['ip', 'port']:
            kwargs[key] = d.get(key)
        return cls(**kwargs)

    def __str__(self):
        return '%s:%s' % (self.ip, self.port)

    def serialize(self, vds=None):
        if not vds:
            vds = BCDataStream()
        # IPv4-mapped IPv6 address.
        vds.write('00000000000000000000ffff'.decode('hex'))

        ip = map(int, self.ip.split('.'))
        for i in ip:
            vds.write_uchar(i)
        # Ports are encoded as big-endian.
        vds._write_num('>H', self.port)
        return vds.input.encode('hex')

    def dump(self):
        return {'ip': self.ip, 'port': self.port}

class MasternodePing(object):
    """A masternode ping message."""
    @classmethod
    def deserialize(cls, vds):
        vin = parse_input(vds)
        block_hash = hash_encode(vds.read_bytes(32))
        sig_time = vds.read_int64()
        sig = vds.read_bytes(vds.read_compact_size())
        return cls(vin=vin, block_hash=block_hash, sig_time=sig_time, sig=sig)

    @classmethod
    def from_dict(cls, d):
        kwargs = {}
        for key in ['vin', 'block_hash', 'sig_time', 'sig']:
            kwargs[key] = d.get(key)
        if kwargs.get('vin'):
            kwargs['vin'] = util.utfify(kwargs['vin'])
        if kwargs.get('sig'):
            kwargs['sig'] = base64.b64decode(kwargs['sig'])
        return cls(**kwargs)

    def __init__(self, vin=None, block_hash='', sig_time=0, sig=''):
        if vin is None:
            vin = {'prevout_hash':'', 'prevout_n': 0, 'scriptSig': '', 'sequence':0xffffffff}
        self.vin = vin
        self.block_hash = block_hash
        self.sig_time = int(sig_time)
        self.sig = sig

    def serialize(self, vds=None):
        if not vds:
            vds = BCDataStream()
        serialize_input(vds, self.vin)
        vds.write(hash_decode(self.block_hash))
        vds.write_int64(self.sig_time)
        vds.write_string(self.sig)
        return vds.input.encode('hex')

    def serialize_for_sig(self, update_time=False):
        s = serialize_input_str(self.vin)
        s += self.block_hash

        if update_time:
            self.sig_time = int(time.time())
        s += str(self.sig_time)
        return s

    def sign(self, wif, delegate_pubkey=None, current_time=None):
        """Sign this ping.

        If delegate_pubkey is specified, it will be used to verify the signature.
        If current_time is specified, sig_time will not be updated.
        """
        update_time = True
        if current_time is not None:
            self.sig_time = current_time
            update_time = False

        eckey = bitcoin.regenerate_key(wif)
        serialized = unicode(self.serialize_for_sig(update_time=update_time)).encode('utf-8')

        if not delegate_pubkey:
            delegate_pubkey = bitcoin.public_key_from_private_key(wif).decode('hex')
        self.sig = eckey.sign_message(serialized, bitcoin.is_compressed(wif))
        return self.sig

    def dump(self):
        sig = base64.b64encode(self.sig)
        return {'vin': self.vin, 'block_hash': self.block_hash, 'sig_time': self.sig_time, 'sig': sig}

def serialize_input(vds, vin):
    vds.write(hash_decode(vin['prevout_hash']))
    vds.write_uint32(vin['prevout_n'])
    vds.write_string(vin['scriptSig'])
    vds.write_uint32(vin['sequence'])

def serialize_input_str(vin):
    """Used by MasternodePing in its serialization for signing."""
    s = ['CTxIn(']
    s.append('COutPoint(%s, %s)' % (vin['prevout_hash'], vin['prevout_n']))
    s.append(', ')
    if vin['prevout_hash'] == '00'*32 and vin['prevout_n'] == 0xffffffff:
        s.append('coinbase %s' % vin['scriptSig'])
    else:
        scriptSig = vin['scriptSig']
        if len(scriptSig) > 24:
            scriptSig = scriptSig[0:24]
        s.append('scriptSig=%s' % scriptSig)

    if vin['sequence'] != 0xffffffff:
        s.append(', nSequence=%d' % vin['sequence'])
    s.append(')')
    return ''.join(s)

class MasternodeAnnounce(object):
    """A masternode announce message.

    Attributes:
        - alias: Alias to help the user identify this masternode.
        - vin: 1K zaap input.
        - addr: Address that the masternode can be reached at.
        - collateral_key: Key that can spend the 1K zaap input.
        - delegate_key: Key that the masternode will sign messages with.
        - sig: Message signature.
        - sig_time: Message signature creation time.
        - protocol_version: The masternode's protocol version.
        - last_ping: The last time the masternode pinged the network.
        - last_dsq: The last time the masternode sent a DSQ (darksend) message.
        - announced: Whether this announce has been broadcast.

    """
    def __init__(self, alias='', vin=None, addr=NetworkAddress(), collateral_key='', delegate_key='',
                 sig='', sig_time=0, protocol_version=70201, last_ping=MasternodePing(),
                 last_dsq=0, announced=False):
        self.alias = alias
        if vin is None:
            vin = {'prevout_hash':'', 'prevout_n': 0, 'scriptSig': '', 'sequence':0xffffffff}
        self.vin = vin
        self.addr = addr
        self.collateral_key = collateral_key
        self.delegate_key = delegate_key
        self.sig = sig
        self.sig_time = int(sig_time)
        self.protocol_version = protocol_version
        self.last_ping = last_ping
        self.last_dsq = last_dsq
        self.announced = announced

    @classmethod
    def deserialize(cls, raw):
        vds = BCDataStream()
        vds.write(raw.decode('hex'))
        vin = parse_input(vds)
        address = NetworkAddress.deserialize(vds)
        collateral_pubkey = vds.read_bytes(vds.read_compact_size()).encode('hex')
        delegate_pubkey = vds.read_bytes(vds.read_compact_size()).encode('hex')

        sig = vds.read_bytes(vds.read_compact_size())
        sig_time = vds.read_int64()

        protocol_version = vds.read_uint32()

        last_ping = MasternodePing.deserialize(vds)

        last_dsq = vds.read_int64()

        kwargs = {'vin': vin, 'addr': address, 'collateral_key': collateral_pubkey,
                    'delegate_key': delegate_pubkey, 'sig': sig, 'sig_time': sig_time,
                    'protocol_version': protocol_version, 'last_ping': last_ping, 'last_dsq': last_dsq}
        return cls(**kwargs)

    def get_hash(self):
        vds = BCDataStream()
        serialize_input(vds, self.vin)
        vds.write_string(self.collateral_key.decode('hex'))
        vds.write_int64(self.sig_time)
        return hash_encode(bitcoin.Hash(vds.input))

    def serialize(self, vds=None):
        if not vds:
            vds = BCDataStream()
        serialize_input(vds, self.vin)
        self.addr.serialize(vds)
        vds.write_string(self.collateral_key.decode('hex'))
        vds.write_string(self.delegate_key.decode('hex'))
        vds.write_string(self.sig)
        vds.write_int64(self.sig_time)
        vds.write_uint32(self.protocol_version)
        self.last_ping.serialize(vds)
        vds.write_int64(self.last_dsq)

        return vds.input.encode('hex')

    def serialize_for_sig(self, update_time=False):
        """Serialize the message for signing."""
        if update_time:
            self.sig_time = int(time.time())

        s = str(self.addr)
        s += str(self.sig_time)

        if self.protocol_version < 70201:
            # Decode the hex-encoded bytes for our keys.
            s += self.collateral_key.decode('hex')
            s += self.delegate_key.decode('hex')
        else:
            # Use the RIPEMD-160 hashes of our keys.
            s += bitcoin.hash_encode(bitcoin.hash_160(self.collateral_key.decode('hex')))
            s += bitcoin.hash_encode(bitcoin.hash_160(self.delegate_key.decode('hex')))

        s += str(self.protocol_version)
        return s

    def get_collateral_str(self):
        """Get the collateral as a string used to identify this masternode."""
        if not self.vin:
            return
        return '%s-%d' % (self.vin['prevout_hash'], self.vin['prevout_n'])

    @classmethod
    def from_dict(cls, d):
        kwargs = {}
        for key in ['alias', 'vin', 'collateral_key', 'delegate_key', 'sig', 'sig_time',
                    'protocol_version', 'last_dsq', 'announced']:
            kwargs[key] = d.get(key)

        vin = kwargs.get('vin')
        if vin:
            kwargs['vin'] = util.utfify(vin)
        sig = kwargs.get('sig')
        if sig:
            kwargs['sig'] = base64.b64decode(sig)
        addr = d.get('addr')
        if addr:
            kwargs['addr'] = NetworkAddress.from_dict(addr)
        last_ping = d.get('last_ping')
        if last_ping:
            kwargs['last_ping'] = MasternodePing.from_dict(last_ping)

        return cls(**kwargs)

    def dump(self):
        kwargs = {}
        for key in ['alias', 'vin', 'collateral_key', 'delegate_key', 'sig_time',
                    'protocol_version', 'last_dsq', 'announced']:
            kwargs[key] = getattr(self, key)

        if self.sig:
            kwargs['sig'] = base64.b64encode(self.sig)
        if self.addr:
            kwargs['addr'] = self.addr.dump()
        if self.last_ping:
            kwargs['last_ping'] = self.last_ping.dump()

        return kwargs

    def sign(self, wif, current_time=None):
        """Sign the masternode announce message.

        If current_time is specified, sig_time will not be updated.
        """
        update_time = True
        if current_time is not None:
            self.sig_time = current_time
            update_time = False
        eckey = bitcoin.regenerate_key(wif)

        serialized = self.serialize_for_sig(update_time=update_time)
        self.sig = eckey.sign_message(serialized, bitcoin.is_compressed(wif))
        return self.sig

    def verify(self, addr=None):
        """Verify that our sig is signed with addr's key."""
        if not addr:
            addr = bitcoin.public_key_to_p2pkh(self.collateral_key.decode('hex'))
        return bitcoin.verify_message(addr, self.sig, self.serialize_for_sig())

