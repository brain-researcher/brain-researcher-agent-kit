# Login And Access

## Current Login Endpoint (Sherlock 2)

Use:

```bash
ssh <sunet>@login.sherlock.stanford.edu
```

Expect Duo/2FA prompt.

## First-Time Access Checklist

1. SUNet account enabled for Sherlock.
2. PI or admin requested needed group filesystem access (for example, OAK group path).
3. Duo/2FA works for SSH login.

If login is denied, verify account enablement and group access before debugging shell config.

## Optional SSH Config (Local Convenience)

```sshconfig
Host sherlock
  HostName login.sherlock.stanford.edu
  User <sunet>
  ForwardX11 no
```

Then login with:

```bash
ssh sherlock
```

## Legacy Note

Sherlock 1 guidance (Kerberos-specific flow) is legacy and should only be used when explicitly required by the user.
