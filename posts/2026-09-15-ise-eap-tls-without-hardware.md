---
title: "EAP-TLS on Cisco ISE 3.5: what the defaults let through, and how we proved it without a single switch"
date: 2026-09-15
summary: A revoked certificate got full access, a certificate with no clientAuth was accepted, and a dead OCSP responder went unnoticed. All measured on ISE 3.5 with openssl, eapol_test and radclient, and no network hardware at all.
draft: false
---

EAP-TLS has a reputation as the strong option for network access: every device proves who it is with a certificate, and nobody types a password. That reputation assumes the policy server checks what you think it checks. On Cisco ISE 3.5 several of those checks are off by default, or are not done at all, and nothing on screen tells you.

This post covers what we measured, and then exactly how we measured it: a certificate authority built with openssl, 802.1X and MAB driven by open-source RADIUS test tools, and not one switch, access point or real endpoint.

Everything was observed on **ISE 3.5.0.527, patch 3**. Behaviour on other versions may differ, which is rather the point of measuring it.

## Finding 1: importing a CA does not turn on revocation checking

You import your issuing CA into the trusted certificate store, tick it for client authentication, and build your policy. It feels finished.

It is not. On the imported CA, OCSP validation was **off**, CRL download was **off** and no OCSP service was selected. We revoked a certificate at the CA, published a fresh CRL, and presented it. It was accepted and placed in the **full office VLAN**.

Revocation only started working once OCSP validation was explicitly enabled on the trust entry and pointed at a responder. Nothing warns you in between. If you have ever revoked a lost laptop's certificate and assumed that closed the door, check this setting.

## Finding 2: when the OCSP responder is down, ISE fails open

With revocation checking on, we stopped the OCSP responder on purpose and presented two certificates, one valid and one revoked.

| OCSP responder | Reject if unreachable | Valid certificate | Revoked certificate |
|---|---|---|---|
| up | off (default) | accept, office VLAN | **reject** |
| **down** | **off (default)** | accept, office VLAN | **ACCEPT, office VLAN** |
| down | on | **reject** | reject |
| up again | on | accept, office VLAN | reject |

The default is fail-open, and it is silent. A certificate you have definitely revoked gets full access while the responder is unreachable, and the Access-Accept looks identical to a healthy one.

Switching on *Reject the request if OCSP Responder is unreachable* gives fail-closed, but read row three: then an outage rejects **everyone**, valid users included. Recovery was clean once the responder came back.

This is a real trade-off between availability and integrity, and it belongs to the business, not to whoever clicked through the wizard:

- **Fail-open:** a responder outage quietly turns revocation off.
- **Fail-closed:** a responder outage becomes a site-wide authentication failure.

Fail-closed is only responsible with a highly available responder. If that is not fundable, say plainly that revocation is best-effort. Our lab now runs fail-closed, so a dead responder shows up as failed tests rather than silent accepts.

## Finding 3: a 24-hour OCSP cache hides all of the above

The OCSP client profile caches responses for **1,440 minutes** by default. At that setting a certificate revoked this morning keeps working until tomorrow, and a responder that died an hour ago goes unnoticed for a day.

We set the cache to one minute for testing. Any revocation test that does not account for the cache is measuring the cache, not the policy.

## Finding 4: clientAuth is not enforced on client certificates

Our design gives each device class its own extended key usage OID, alongside the standard `clientAuth` usage that says "this certificate may be used to authenticate a client". The design listed "clientAuth missing" as something that must be rejected, on the reasonable assumption that the policy server checks it.

So we issued a certificate that carried the device-class OID and **no clientAuth at all**:

```
$ openssl x509 -in office-no-clientauth.crt -noout -ext extendedKeyUsage
X509v3 Extended Key Usage:
    1.3.6.1.4.1.99999.1.1.1
```

ISE accepted it for EAP-TLS and returned the full office VLAN.

The consequence is bigger than one missing check. If the platform ignores clientAuth, the class OID becomes the *only* gate. On a site with a shared enterprise CA, a certificate issued for something else entirely could carry that OID and get office access.

**The fix is in policy, not the platform.** ISE exposes `CERTIFICATE: Extended Key Usage - Name` as a condition, so the authorisation rule now requires both:

```
CERTIFICATE: Extended Key Usage - OID   EQUALS  <office class OID>
CERTIFICATE: Extended Key Usage - Name  EQUALS  clientAuth
```

Re-tested, the same certificate now lands in quarantine, and the valid office certificate is unaffected.

There is a sting in the tail. A month later we found the fix had been applied to the office rule only. Both OT rules still checked the class OID without clientAuth, and nothing in the test suite would have caught it, because we had a no-clientauth certificate for the office class but not for OT. Both rules are now fixed and confirmed by reading the configuration back; the matching OT test certificate is written and its case is waiting to run. The lesson: a compensating control that lives in policy has to be tested **per rule**, or someone rebuilding one rule silently brings the weakness back.

## Finding 5: binding a certificate to hardware works, if the MAC format matches exactly

For OT and IoT devices we wanted a certificate that only works on the device it was issued to. The device's MAC address goes into the certificate's Subject Alternative Name, and the rule compares it with the MAC the switch reports in `Calling-Station-Id`:

```
CERTIFICATE: Extended Key Usage - OID        EQUALS  <OT class OID>
CERTIFICATE: Subject Alternative Name - DNS  EQUALS  Radius:Calling-Station-ID
IdentityGroup: Name                          EQUALS  <registered OT devices>
```

The middle line compares one attribute with another. In the API that is a field that sits `null` on every ordinary condition, and it is the entire mechanism.

It works: a certificate exported and presented from different hardware is quarantined. But the comparison is a **literal string compare**:

| MAC in the certificate | Presented from | Result |
|---|---|---|
| `AA-BB-CC-DD-EE-FF` | same device | OT VLAN |
| `AA-BB-CC-DD-EE-FF` | different device | quarantine |
| `aabbccddeeff` (same MAC) | same device | quarantine |
| `AABBCCDDEEFF` (same MAC) | same device | quarantine |

The certificate authority must mint the MAC in exactly the format the authenticator sends, and that format depends on the switch or controller vendor. Measure it before you issue a single certificate.

Two honest limits. First, identity extraction does not validate that the SAN is a MAC at all: a SAN of `ot-dotted.lab.example` authenticated happily. Second, `Calling-Station-Id` is reported by the switch, not proven by the device. The binding stops certificate transplant; it does not stop someone who controls a switch or can spoof a MAC on the wire. Say so rather than oversell it.

## How we tested all of this without hardware

The key idea is simple. **ISE cannot tell whether a RADIUS request came from a switch or from a script.** It sees an Access-Request from an IP address registered as a network device, signed with the right shared secret. So we registered a Linux test VM as that network device and had it speak RADIUS directly.

The whole lab is three virtual machines:

| VM | Role |
|---|---|
| Policy server | ISE 3.5, the device under test |
| Services host | Certificate authority, OCSP responder, CRL web server, DNS, NTP |
| Test host | `eapol_test` for 802.1X, `radclient` for MAB, `tcpdump` for captures |

No switch, no access point, no endpoints. What this tests is the policy server's decisions. What it deliberately does not test is switch behaviour: port control, downloadable ACL enforcement and change of authorisation are out of scope.

### A certificate authority with openssl

A two-tier PKI: a root CA, and an issuing CA signed by it with `pathlen:0` so it cannot sign further CAs. The issuing CA also signs a dedicated OCSP responder certificate with the `OCSPSigning` usage.

Each device class is an openssl extension section. The SAN comes from an environment variable, so one section serves many certificates:

```
[ v3_office ]
basicConstraints        = CA:FALSE
keyUsage                = critical, digitalSignature, keyEncipherment
extendedKeyUsage        = clientAuth, 1.3.6.1.4.1.99999.1.1.1
subjectAltName          = $ENV::SAN
authorityInfoAccess     = OCSP;URI:http://ca.lab.example:2560
crlDistributionPoints   = URI:http://ca.lab.example/crl/issuing-ca.crl
```

(The `99999` arc is a placeholder, not a registered enterprise number.) A negative variant is just another section: `v3_office_no_clientauth` is identical except that `extendedKeyUsage` lists only the class OID.

The interesting part is the **corpus**: a set of certificates where each one is wrong in exactly one way. Issuing one looks like this:

```bash
export SAN="DNS:ws-office-001.lab.example"
openssl genrsa -out office-valid.key 2048
openssl req -new -sha256 -key office-valid.key \
    -subj "/O=BlueCore Lab/CN=WS-OFFICE-001" -out office-valid.csr
openssl ca -config openssl-ca.cnf -batch \
    -extfile class-office.cnf -extensions v3_office \
    -in office-valid.csr -out office-valid.crt
```

The broken ones only change a flag or two:

```bash
# expired: validity window entirely in the past
openssl ca ... -extensions v3_office -startdate 20240101000000Z -enddate 20240201000000Z

# not yet valid (also catches clock skew)
openssl ca ... -extensions v3_office -startdate 20300101000000Z -enddate 20310101000000Z

# revoked: issue normally, then revoke and publish a fresh CRL
openssl ca -config openssl-ca.cnf -revoke office-revoked.crt
openssl ca -config openssl-ca.cnf -gencrl -out issuing-ca.crl

# wrong issuer: signed by a throwaway "rogue" CA outside the trust store
openssl x509 -req -in office-rogue.csr -CA rogue-ca.crt -CAkey rogue-ca.key \
    -CAcreateserial -days 825 -extfile class-office.cnf -extensions v3_office \
    -out office-wrong-issuer.crt
```

The corpus ended up at 27 certificates. The ones that carried the findings above:

| Certificate | What it must prove |
|---|---|
| `office-valid` | the baseline authenticates |
| `office-expired`, `office-notyet` | the validity window is enforced |
| `office-revoked` | revocation is actually checked, not just configured |
| `office-wrong-issuer` | a chain outside the trust anchor is rejected |
| `office-no-clientauth` | extended key usage is enforced |
| `office-wrong-eku` | the class OID discriminates, not merely exists |
| `otiot-valid` | a MAC-bound certificate works on its own device |
| `mac-bare-lower`, `mac-bare-upper`, ... | which SAN formats bind and which do not |

Because some certificates are deliberately expired or not yet valid, **time matters**. The services host runs chrony as the lab's time source. A skewed clock quietly turns a negative test into a false pass.

### An OCSP responder you can switch off

openssl ships a small OCSP responder. It is a test tool, single-threaded and not for production, but it reads the CA's own database, so revoking a certificate takes effect immediately:

```bash
openssl ocsp -index /opt/lab-ca/issuing/index.txt \
    -CA issuing-ca.crt -rsigner ocsp.crt -rkey ocsp.key \
    -port 2560 -text
```

We run it as its own systemd unit, separate from the web server that publishes the CRL, for one reason: so it can be killed on demand.

```bash
sudo systemctl stop lab-ocsp     # responder unreachable
sudo systemctl start lab-ocsp    # responder back
```

That is the entire fail-open experiment from finding 2. A lab that cannot produce a failure on demand cannot make a claim about it.

### 802.1X with eapol_test

`eapol_test` comes from the wpa_supplicant source tree. It is a complete 802.1X supplicant that talks RADIUS straight to the server, skipping the switch. The distribution packages do not include it, so it is built from source:

```bash
cd wpa_supplicant-2.12/wpa_supplicant
cp defconfig .config
echo 'CONFIG_EAPOL_TEST=y' >> .config
make eapol_test
```

Each test is a small supplicant config naming one certificate from the corpus:

```
network={
    key_mgmt=IEEE8021X
    eap=TLS
    identity="WS-OFFICE-001"
    ca_cert="chain.pem"
    client_cert="office-valid.crt"
    private_key="office-valid.key"
}
```

And the run pretends to be a switch port:

```bash
eapol_test -c office-valid.conf \
    -a 192.0.2.10 -p 1812 -s "$RADIUS_SHARED_SECRET" \
    -M aa:bb:cc:00:11:22 \
    -N 4:x:c000020b \
    -N 61:d:15 \
    -r0
```

`-M` sets `Calling-Station-Id`. The `-N` options add RADIUS attributes by number, and both of these cost us time before we added them:

- **`-N 61:d:15` sets NAS-Port-Type to Ethernet.** eapol_test defaults to 19, *wireless*, even for what you think is a wired test. It did not matter until we built a wireless policy set, at which point every "wired" test would have matched it.
- **`-N 4:x:...` sets NAS-IP-Address** (hex for 192.0.2.11 here). The default is 127.0.0.1. If your policy sets are selected by device address, the request silently lands in the default set and gets an Access-Accept with **no authorisation attributes at all**, which looks like success.

A successful run ends with the result and the VLAN:

```
RADIUS message: code=2 (Access-Accept) identifier=10 length=269
   Attribute 64 (Tunnel-Type) length=6
      Value: 0100000d
   Attribute 81 (Tunnel-Private-Group-Id) length=5
      Value: 013130
...
SUCCESS
```

`013130` is a tag byte `01` followed by ASCII `10`: VLAN 10.

### MAB with radclient

MAC Authentication Bypass is even simpler, because there is no EAP conversation at all. The switch sends the MAC as both username and password with `Service-Type = Call-Check`. `radclient`, from the FreeRADIUS utilities package, sends exactly that:

```bash
cat <<'EOF' | radclient -x -t 5 -r 1 192.0.2.10:1812 auth "$RADIUS_SHARED_SECRET"
User-Name = "aabbcc000001"
User-Password = "aabbcc000001"
Service-Type = Call-Check
Calling-Station-Id = "AA:BB:CC:00:00:01"
NAS-Port-Type = Ethernet
NAS-IP-Address = 192.0.2.11
NAS-Port = 0
EOF
```

```
Received Access-Accept Id 18 from 192.0.2.10:1812 to 192.0.2.11:57540
    User-Name = "AA-BB-CC-00-00-01"
    Tunnel-Type:1 = VLAN
    Tunnel-Medium-Type:1 = IEEE-802
    Tunnel-Private-Group-Id:1 = "30"
```

The negative MAB cases are just as cheap: an unregistered MAC must be rejected, and a request with no NAS-Port-Type at all must fail rather than fall through to something permissive.

### Tests as data, not scripts

Every case is a small YAML file that says what to send and what must come back, never how to send it:

```yaml
id: OFFICE-TLS-007-revoked
tier: office
method: eap-tls
cert: office-revoked
send: { calling-station-id: "aa:bb:cc:00:11:28" }
expect:
  result: reject
forbid: [any-vlan]
status: active
```

A small Python runner turns each case into an eapol_test or radclient call, parses the reply and records a result. Three rules keep the results honest:

1. **`forbid` is mandatory.** A case must say what must *not* come back, even if the answer is an explicit empty list, so "checked nothing" can never pass for "found nothing".
2. **Roles are abstract.** A case says `ROLE_OFFICE`, not "VLAN 10". A per-platform mapping file translates it, so the same cases can run against another vendor's policy server unchanged.
3. **Every result names the configuration it ran against.** The runner refuses to write a result without the git commit of the captured ISE configuration. A result that cannot say what it tested is not evidence.

Most of the suite is negative on purpose: expired, not yet valid, revoked, wrong issuer, missing clientAuth, wrong device class, transplanted certificate, unregistered device, wrong network. A design tested only with valid credentials proves nothing about rejection.

### Packet captures, and a surprise about fragments

We captured the RADIUS traffic with `tcpdump` on the test host while the cases ran. Because this EAP-TLS negotiates TLS 1.2, the certificates travel in cleartext inside the handshake, so the capture shows the policy server presenting the certificate from our lab CA. That is the server certificate binding demonstrated on the wire, not inferred from a settings page.

The capture also showed the client's certificate exchange **fragmenting at the IP layer**. That matters in the field: firewalls, load balancers and some WAN paths drop IP fragments, and when they do EAP-TLS fails in a way that looks like a certificate or policy problem. If RADIUS crosses a firewall on your site, check fragment handling before you debug certificates.

## What to check on your own deployment

1. Open each trusted CA used for client authentication and confirm OCSP or CRL checking is actually **enabled**.
2. Decide fail-open or fail-closed deliberately, write the decision down, and fund responder redundancy if you choose fail-closed.
3. Look at the OCSP response cache. A day is a long time for a revoked certificate.
4. Add `Extended Key Usage - Name EQUALS clientAuth` to every certificate authorisation rule, and test each rule with a certificate that lacks it.
5. If you bind certificates to MAC addresses, measure the exact `Calling-Station-Id` format your switches and controllers send before issuing anything.
6. Keep one deliberately broken certificate for every check you rely on, and run them after every change.

None of this needed a hardware budget. It needed a CA you control, a responder you can switch off, two free RADIUS test tools, and the habit of testing the rejections as carefully as the successes.
