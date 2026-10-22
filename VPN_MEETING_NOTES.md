# VPN Meeting — What To Say

## THE ONE COMMAND

```
ssh root@41.59.229.104
/root/vpntest.sh
```

Read the VERDICT at the bottom out loud. That's all.
When anyone says "try now" — run it again.

---

## IF THEY ASK YOU SOMETHING

**"Did you configure the VPN?"**
> "No. NIDC configured it on their gateway 41.59.225.34.
>  Our server has no VPN software installed at all."

**"Which phase is down?"**
> "We cannot see the phases. There is no IPsec on our server —
>  the tunnel is on NIDC's gateway. NIDC can show you."

Run if needed:  `ip xfrm state`   (prints nothing = no VPN here)

**"Is your firewall blocking us?"**
> "No. Our firewall is inactive and every rule is set to ACCEPT.
>  No YAS address is blocked anywhere."

Run if needed:  `ufw status`  and  `iptables -L -n`

**"It must be your server."**
> "Our server answers the public internet on port 443 in
>  0.09 seconds. It does not answer through the tunnel.
>  Same server, same port, same moment.
>  If our server were the problem, both would fail."

**"Can you test now?"**
> Run `/root/vpntest.sh` and read the verdict.

**"Can you telnet to us?"**
> Run: `nc -zv 41.222.176.233 8443`
> Result: timeout, no response.

**"What is your test IP and port?"**
> "IP: 41.59.229.104.  Port: TCP 443, listening now.
>  You can telnet to us any time."

---

## WHAT YOU SHOULD ASK THEM

**To NIDC:**
1. "Is the Phase 2 SA up for 41.59.229.104 to 41.222.176.0/24
    and 41.222.182.0/24?  Phase 1 being up is not enough."
2. "Is the NAT (10.105.1.34 to 41.59.229.104) applied BEFORE
    the IPsec match?  If after, our packets carry source
    10.105.1.34, which is outside the encryption domain,
    and would be dropped silently."

**To YAS:**
3. "Do you see ANY traffic from 41.59.229.104 in your logs?"
   - They see packets -> their firewall is dropping them
   - They see nothing -> packets never left NIDC

4. "Was Rule 1 on the VPN form provisioned? Its Action and
    Duration columns are blank, unlike Rules 3 and 4."

5. "Is the service on 41.222.176.233:8443 actually running?
    Can someone telnet to it from inside YAS?"

---

## THE FACTS YOU HAVE (tested many times)

| What | Result |
|---|---|
| EasyFix -> YAS through tunnel | timeout, no answer |
| YAS -> EasyFix through tunnel | timeout (their own test) |
| Internet -> EasyFix port 443 | connects in 0.09 seconds |
| EasyFix -> Internet | works |
| Traceroute to YAS | dies at hop 1, no reply |
| Traceroute to internet | 6 hops, arrives in 39 ms |
| Our firewall | inactive, everything ACCEPT |
| VPN software on our server | none installed |

**Our packets stop at gateway 10.105.1.33 and never reach YAS.**

---

## WHAT WE STILL NEED FROM YAS (even after the tunnel works)

1. Merchant ID and API credentials
2. API documentation
3. Sandbox / test account
4. Callback format - how they notify us a payment succeeded,
   and how it is signed so we can verify it is really them

Without these we cannot build the payment integration even
with a working tunnel. Ask for them in this meeting.

---

## IF YOU GET STUCK

Say: "Let me check and come back to you."
Then message me and I will test and explain.

You do not have to answer anything on the spot.
