---
title: Launching and Connecting to an EC2 instance
description: In this cookbook we describe how you can launch and connect to an EC2 instance.
---
import useBaseUrl from '@docusaurus/useBaseUrl';

We receive a lot of questions on how to connect to an EC2 instance. The easiest available option to connect to your instance is by using the [AWS Session Manager](https://docs.aws.amazon.com/de_de/systems-manager/latest/userguide/session-manager.html).

<!--truncate-->

## Prerequisites for using AWS Session Manager (SSM)

Prerequisites to connect to an EC2 instance using SSM:

1. a role needs to be attached to the instance allowing access of the instance to the session manager API (we predeploy **DTIT\_SecureSSMRole** into all DTIT project accounts for this purpose)
2. **SSM Agent** must be installed on the instance (pre-installed per default on most AWS-provided AMIs)
3. network connectivity to session manager API needs to be available
  - given in all public subnets
  - if the EC2 instance is in a private subnet a route to the session manager API needs to be configured (either via a NAT gateway or via a VPC endpoint). **Note that blue and green VPCs shared with your account provide the required endpoints already.**
4. IAM user needs to have permission to work with session manager (given for role DTIT_Project_Admin)

<img alt="Session Manager Architecture" src={useBaseUrl('img/ec2-session-manager.png')} />

## Launching an EC2 instance

1. Click Services, Choose EC2.
2. Make sure your selected region in the top-right corner is Frankfurt (eu-central-1)

<img alt="Select Region" src={useBaseUrl('img/ec2-region.png')} />

3. Now you are ready to deploy your EC2 instance. To start the process click „Launch Instance&quot;
4. The process consists of 7 steps, in the first step choose your AMI (Amazon Machine Image – Operating System). Note that not all of the AMIs have SSM Agent preinstalled. In such cases see
[https://aws.amazon.com/premiumsupport/knowledge-center/install-ssm-agent-ec2-linux/](https://aws.amazon.com/premiumsupport/knowledge-center/install-ssm-agent-ec2-linux/)

<img alt="Launch instance process" src={useBaseUrl('img/ec2-launch-instance.png')} />


5. In the 2nd step you choose your instance type – based on your workload. Amazon also offers Free Tier instances, which are recommended for testing purposes. Click „Next: Configure Instance Details&quot;
6. In the step 3 choose your VPC (network) and Subnet. Choose proper Public IP assignment settings and attach the following IAM role: **DTIT_SecureSSMRole**

<img alt="Configure Details" src={useBaseUrl('img/ec2-configure-details.png')} />


7. Add Storage, then Click Next
8. Add Tags, then Click Next
9. Configure Security Group. Create new or choose an existing one. Make sure you specify a name and description.

<img alt="Configure Details" src={useBaseUrl('img/ec2-configure-sg.png')} />

For system access via session manager the security group actually can be empty (no ports for incoming traffic required). For blue/green VPC you can use one of the predeployed security groups.

10. Click "Review and Launch", then "Launch"

## Connecting to an EC2 instance using Systems Manager (SSM)

Easiest way is to use the Connect button in the EC2 console (next to "Launch instance") and then select connect via session manager.

<img alt="Configure Details" src={useBaseUrl('img/ec2-connect-1.png')} />

Alternatively you can go through session manager service:

1. Click Services, choose "Systems Manager"
2. In the left navigation pane choose "Session Manager"
3. Here you can configure the session manager preferences (like logging and encryption) according to your requirements.
4. Click "Start Session"
5. Choose the instance you want to connect to and click "Start session"

<img alt="Configure Details" src={useBaseUrl('img/ec2-connect-2.png')} />

### Connect to an EC2 instance in the private subnet of the Magenta VPC

**Deploy NAT Gateway**

1. Services, VPC
2. NAT Gateway
3. Create a NAT Gateway
  - Specify your subnet where you want to deploy it – it needs to be deployed into public subnet, prefer MagentaPublic1
  - Elastic IP is a public IP address which will be used by the NAT Gateway. If there is no EIP created in your account click the **Create New EIP** button
4. Finish

**Modify the MagentaPrivateRouteTable**

1. Click Route Tables
2. Find and mark MagentaPrivateRouteTable
3. Click Routes
4. Edit Routes
5. Add a default route, where the target will be the NAT Gateway created in the previous step

<img alt="Configure Details" src={useBaseUrl('img/ec2-nat.png')} />


- After modifying the route table instances in all of the private subnets of MagentaVPC will be reachable using SSM (Systems Manager), because the route table we changed is associated with all of the private subnets.

## Alternative option: SSH via Telekom Special Internet Proxy

- [https://yam-united.telekom.com/pages/internet-connect/apps/wiki/wiki/list/view/4636fd63-cf52-453d-8f9d-d9e874986f5e](https://yam-united.telekom.com/pages/internet-connect/apps/wiki/wiki/list/view/4636fd63-cf52-453d-8f9d-d9e874986f5e)


## Hardened machine images (AMIs)

Hardened AMIs from DevSecOps are available and can be used as follows: 
- go to your AWS account
- then EC2 -> Instances -> My AMIs
- then tick on "Shared with me" and you should see images like "devsecops-amazon2-\*" or "devsecops-redhat-\*"
- select the latest one (for example "DevSecOps-redhat7-200315 - ami-04468c31caac21298"), the greater the number – the later is the image. 

Get in touch with DevSecOps ([devsecops@telekom.de](mailto:devsecops@telekom.de)) if you experience any issues or have questions about this.

Also Ansible hardening scripts and testing script is available on github, you can take a look at `check_linux.sh`: [https://github.com/telekom/tel-it-security-automation/tree/master/hardening-linux-server/testing](https://github.com/telekom/tel-it-security-automation/tree/master/hardening-linux-server/testing)

