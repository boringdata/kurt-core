---
title: Managing Domains - Resend
url: https://resend.com/docs/dashboard/domains/introduction
hostname: resend.com
description: Visualize all the domains on the Resend Dashboard.
sitename: Resend
date: 2025-12-08
---
## Verifying a domain

Resend sends emails using a domain you own. We recommend using subdomains (e.g.,`updates.yourdomain.com`

) to isolate your sending reputation and communicate your intent. Learn more about [using subdomains](https://resend.com/docs/knowledge-base/is-it-better-to-send-emails-from-a-subdomain-or-the-root-domain). In order to verify a domain, you must set two DNS entries:

[SPF](https://resend.com#what-are-spf-records): list of IP addresses authorized to send email on behalf of your domain[DKIM](https://resend.com#what-are-dkim-records): public key used to verify email authenticity

[DMARC record](https://resend.com/docs/dashboard/domains/dmarc)to build additional trust with mailbox providers.

Resend requires you own your domain (i.e., not a shared or public domain).

## View domain details

The[Domains dashboard](https://resend.com/domains)shows information about your domain name, its verification status, and history.

Need specific help with a provider? View our

[knowledge base DNS Guides](https://resend.com/docs/knowledge-base).## What are SPF records

Sender Policy Framework (SPF) is an email authentication standard that allows you to list all the IP addresses that are authorized to send email on behalf of your domain. The SPF configuration is made of a TXT record that lists the IP addresses approved by the domain owner. It also includes a MX record that allows the recipient to send bounce and complaint feedback to your domain.## Custom Return Path

By default, Resend will use the`send`

subdomain for the Return-Path address. You can change this by setting the optional `custom_return_path`

parameter when [creating a domain](https://resend.com/docs/api-reference/domains/create-domain)via the API or under

**Advanced options**in the dashboard. For the API, optionally pass the custom return path parameter.

- Must be 63 characters or less
- Must start with a letter, end with a letter or number, and contain only letters, numbers, and hyphens

`testing`

), as they may be exposed to recipients in some email clients.
## What are DKIM records

DomainKeys Identified Mail (DKIM) is an email security standard designed to make sure that an email that claims to have come from a specific domain was indeed authorized by the owner of that domain. The DKIM configuration is made of a TXT record that contains a public key that is used to verify the authenticity of the email.## Understand a domain status

Domains can have different statuses, including:`not_started`

: You’ve added a domain to Resend, but you haven’t clicked on`Verify DNS Records`

yet.`pending`

: Resend is still trying to verify the domain.`verified`

: Your domain is successfully verified for sending in Resend.`failed`

: Resend was unable to detect the DNS records within 72 hours.`temporary_failure`

: For a previously verified domain, Resend will periodically check for the DNS record required for verification. If at some point, Resend is unable to detect the record, the status would change to “Temporary Failure”. Resend will recheck for the DNS record for 72 hours, and if it’s unable to detect the record, the domain status would change to “Failure”. If it’s able to detect the record, the domain status would change to “Verified”.

## Open and Click Tracking

Open and click tracking is disabled by default for all domains. You can enable it by clicking on the toggles within the domain settings.For best deliverability, we recommend disabling click and open tracking

[for sensitive transactional emails](https://resend.com/docs/dashboard/emails/deliverability-insights#disable-click-tracking).## How Open Tracking Works

A 1x1 pixel transparent GIF image is inserted in each email and includes a unique reference to this image file. When the image is downloaded, Resend can tell exactly which message was opened and by whom.## How Click Tracking Works

To track clicks, Resend modifies each link in the body of the HTML email. When recipients open a link, they are sent to a Resend server, and are immediately redirected to the URL destination.## Export your data

Admins can download your data in CSV format for the following resources:- Emails
- Broadcasts
- Contacts
- Segments
- Domains
- Logs
- API keys

Currently, exports are limited to admin users of your team.

All exports your team creates are listed in the

[Exports](https://resend.com/exports)page under**Settings**>**Team**>**Exports**. Select any export to view its details page. All members of your team can view your exports, but only admins can download the data.