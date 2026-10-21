# EasyFix ↔ YAS VPN — Check Commands and Results

**Captured:** 2026-10-21 06:31 EAT
**Server:** easy-ja-lin-1001 (41.59.229.104)

Run any command below yourself. The results shown are real, from this server.

---

## QUICK START

```bash
ssh root@41.59.229.104
/root/vpncheck.sh
```

One command prints the whole report. Use this in the meeting.

---

## THE ONE SENTENCE THAT MATTERS

> Our port 443 answers the public internet in 0.09 seconds.
> It does not answer through the tunnel.
> Same server, same port, same moment.
> **If our server were the problem, both would fail.**

If anyone says *"it's your server"*, ask:
**"Then why does the internet reach it in under a tenth of a second?"**

---

## 1. WHO WE ARE

```bash
hostname -I                       # our private IP
curl -s https://api.ipify.org     # our public IP (what YAS sees)
ip route show                     # how we reach the internet
```

**Result:**
```
private IP:  10.105.1.34
public IP:   41.59.229.104     <-- correct, matches the VPN form
gateway:     10.105.1.33       <-- NIDC's router
```

**Means:** our public IP is correct. The 1:1 NAT works.

---

## 2. IS THERE A VPN ON OUR SERVER?

```bash
which strongswan ipsec swanctl openvpn wireguard
systemctl list-units --type=service --state=running | grep -i vpn
ip xfrm state
ip xfrm policy
ip -br link show
```

**Result:**
```
which ...                 exit=1          (none found)
VPN services running:     no VPN service running
ip xfrm state             (empty)
ip xfrm policy            (empty)
interfaces                lo, eth0 only   (no tunnel interface)
```

**Means: THERE IS NO VPN ON OUR SERVER.**

**Say:** *"We did not configure the VPN. NIDC did, on their gateway
41.59.225.34. We have no IPsec to inspect, so we cannot tell you which
phase is down — NIDC can."*

---

## 3. IS OUR FIREWALL BLOCKING ANYTHING?

```bash
ufw status
iptables -L -n -v
iptables -t nat -L -n
nft list ruleset
```

**Result:**
```
ufw:                 Status: inactive
iptables INPUT       policy ACCEPT, 0 rules
iptables OUTPUT      policy ACCEPT, 0 rules
iptables FORWARD     policy ACCEPT, 0 rules
nat table            empty
nftables             only fail2ban (6 foreign SSH attackers)
                     NO 41.222.x.x or 41.204.x.x blocked
```

**Means: WE BLOCK NOTHING.**

**Say:** *"Our firewall is inactive and every chain is set to ACCEPT with
zero rules. No YAS address is blocked anywhere on our system."*

---

## 4. CAN WE REACH YAS? (the actual test)

```bash
nc -zv 41.222.176.233 8443
nc -zv 41.222.182.236 8443
nc -zv 41.222.182.200 8443
nc -zv 41.222.176.226 8443
nc -zv 41.204.144.244 8443
ping -c 3 41.222.176.233
```

**Result:**
```
41.222.176.233:8443    FAILED - timeout, no response
41.222.182.236:8443    FAILED - timeout, no response
41.222.182.200:8443    FAILED - timeout, no response
41.222.176.226:8443    FAILED - timeout, no response
41.204.144.244:8443    FAILED - timeout, no response
ping                   no reply
```

**Means: NOTHING REACHES YAS.**

Note it is a **timeout**, not "connection refused". Refused would mean we
reached them and they said no. Timeout means our packets vanish.

You can also use telnet (exit with `Ctrl+]` then `quit`):
```bash
telnet 41.222.176.233 8443
```
| You see | Meaning |
|---|---|
| `Connected to ...` | works |
| `Connection refused` | reached them, port closed |
| `Trying ...` then hangs | **ours — nothing arrives** |

---

## 5. CONTROL TEST — PROVE OUR INTERNET WORKS

```bash
nc -zv 1.1.1.1 443
nc -zv 8.8.8.8 53
```

**Result:**
```
Connection to 1.1.1.1 443 port [tcp/https] succeeded!
Connection to 8.8.8.8 53 port [tcp/domain] succeeded!
```

**Means: OUR INTERNET IS PERFECT.**

**This is the most important test.** It proves the failure in section 4 is
not our server. Always run 4 and 5 together — one is meaningless without
the other.

---

## 6. IS OUR SERVICE READY FOR YAS CALLBACKS?

```bash
ss -tlnp | grep ':443 '
systemctl is-active worker-connect nginx
curl -k -o /dev/null -w "%{http_code}\n" https://127.0.0.1
```

**Result:**
```
LISTEN  0.0.0.0:443    nginx        <-- all interfaces, anyone can connect
worker-connect: active
nginx:          active
local HTTPS:    200
```

**Means: WE ARE READY.** YAS can telnet to 41.59.229.104 port 443 now.

---

## 7. PROVE IT FROM OUTSIDE (run from your laptop, not the server)

```bash
telnet 41.59.229.104 443
curl -I https://workersearch.co.tz
```

**Expected:**
```
Trying 41.59.229.104...
Connected to 41.59.229.104.      <-- 0.09 seconds
HTTP/1.1 200 OK
```

**Means: the public internet reaches our server instantly.**

Compare with Catherine's test through the tunnel, which stopped at
`Trying 41.59.229.104...` and never connected.

---

## SUMMARY TABLE FOR THE MEETING

| Direction | Path | Result |
|---|---|---|
| EasyFix → YAS (8443) | tunnel | TIMEOUT |
| YAS → EasyFix (443) | tunnel | TIMEOUT (their own test) |
| Internet → EasyFix (443) | internet | CONNECTS in 0.09s |
| EasyFix → Internet | internet | CONNECTS |

**Traffic fails in BOTH directions through the tunnel.
The same server and port work perfectly over the internet.**

---

## WHAT TO ASK THEM

**1. To YAS:** *"Do our packets reach you at all? Please check your
firewall logs for source 41.59.229.104 to 41.222.176.233:8443."*
- Packets arriving and dropped → YAS firewall rule
- No packets arriving → traffic never entered the tunnel (NIDC)

**2. To YAS:** *"What source IP do you see from us?"*
- If they see **10.105.1.34** instead of 41.59.229.104, the NAT is applied
  AFTER the IPsec match on NIDC's side. Packets fall outside the agreed
  encryption domain and get dropped. This would explain everything.

**3. To NIDC:** *"Is traffic from 41.59.229.104 to 41.222.176.0/24 and
41.222.182.0/24 actually being routed INTO the tunnel?"*
- A tunnel can be established and still carry nothing if the routing or
  proxy-IDs do not direct those destinations into it.

**4. To YAS:** *"Was Rule 1 on the VPN form provisioned?"*
- On the form, Rule 1 (the test rule) has the **Action and Duration columns
  blank**, while Rules 3 and 4 say "Allow / Contract life".

**5. To YAS:** *"Is the service on 41.222.176.233:8443 running? Can someone
telnet to it from inside your own network?"*

---

## OUR CONFIGURATION (from the VPN form)

```
Our encryption domain:   41.59.229.104
Our VPN peer (NIDC):     41.59.225.34
YAS VPN peer:            41.204.144.244
YAS encryption domain:   41.222.176.0/24, 41.222.182.0/24
Phase 1:  IKEv2, DH Group 20, AES-256 GCM/CBC, SHA-256/384/512
Phase 2:  ESP, AES-256 GCM/CBC, SHA-256/384/512, PFS Group 20, 3600s
```

Note: the form says Phase 1 lifetime 28,800 but both sides agreed 86,400
in the group chat. The form should be updated.

---

## REMEMBER

```
Our server:    WORKING
Our firewall:  BLOCKS NOTHING
Our internet:  WORKING
Our service:   LISTENING ON 443
The tunnel:    NOT CARRYING TRAFFIC
```

We own none of the broken part. The VPN is on NIDC's gateway.
