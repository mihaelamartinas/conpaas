#!/bin/sh

# These parameters are used for performing CAPTCHA[1] operations and they are
# issued for a specific domain. To generate a pair of keys for your domain,
# please go to the reCAPTCHA admin page[2] (it's hosted by Google, so you need
# a Google account).
#
# [1] http://www.google.com/recaptcha
# [2] https://www.google.com/recaptcha/admin/create
CAPTCHA_PUBLIC_KEY=""
CAPTCHA_PRIVATE_KEY=""

# Configuration values for Amazon EC2. The script will assume you want to
# deploy ConPaaS on EC2 if AMI_ID is not empty. If you want to use ConPaaS on
# another type of cloud, keep on reading this file.

# This variable contains the identifier of the Amazon Machine Image created
# from the Web hosting service. Your AMIs can be found at
# https://console.aws.amazon.com/ec2/home?region=us-east-1#s=Images
AMI_ID=""

# This variable contains the created security group from the Web hosting
# service. Your security groups can be found at
# https://console.aws.amazon.com/ec2/home?region=us-east-1#s=SecurityGroups
SECURITY_GROUP=""

# This variable contains the Key Pair name  to be used.  Your keypairs can be
# found at https://console.aws.amazon.com/ec2/home?region=us-east-1#s=KeyPairs
KEYPAIR=""

# This variable contains the type of EC2 instances to use. A good value to use
# inexpensive, low-performance instances is "t1.micro".
EC2_INSTANCE_TYPE="t1.micro"

# EC2_USER should be set to your EC2 user name. Beware: this is not the
# email address you normally use to login at the AWS management console. 
# An EC2 user name is a long opaque string. It can be found at
# https://aws-portal.amazon.com/gp/aws/developer/account/index.html?action=access-key#account_identifiers
# under the name "Access key ID"
EC2_USER=""

# EC2_PASSWORD should be set to the corresponding password.
# Again, this is a long opaque string. You can find it next to your
# Access Key ID by clicking "Show Secret Access Key".
EC2_PASSWORD=""

# Amazon Account ID without dashes. Used for identification with Amazon EC2.
# Found in the AWS Security Credentials.
EC2_ACCOUNT_ID=""

# Your CanonicalUser ID. Used for setting access control settings in AmazonS3. Found in the AWS Security
# Credentials.
EC2_CANONICAL_ID=""

###########################################################################
# DON'T CHANGE ANYTHING BELOW THIS LINE UNLESS YOU WANT TO USE OPENNEBULA #
###########################################################################

# Configuration values for OpenNebula. The script will assume you want to
# deploy ConPaaS on OpenNebula if IMAGE is not empty.

# The image ID (an integer). You can list the registered OpenNebula
# images with command "oneimage list" command.
IMAGE=""

# OCCI defines 3 standard instance types: small medium and large. This
# variable should choose one of these.
ON_INSTANCE_TYPE="small"

# Your OpenNebula user name
ON_USER=""

# Your OpenNebula password
ON_PASSWD=""

# The network ID (an integer). You can list the registered OpenNebula
# networks with the "onevnet list" command.
NETWORK=""

# The URL of the OCCI interface at OpenNebula. Note: ConPaaS currently
# supports only the default OCCI implementation that comes together
# with OpenNebula. It does not yet support the full OCCI-0.2 and later
# versions.
URL=""

# The network gateway through which new VMs can route their traffic in
# OpenNebula (an IP address)
GATEWAY=""

# The DNS server that VMs should use to resolve DNS names (an IP address)
NAMESERVER=""

###########################################################################
# DON'T CHANGE ANYTHING BELOW THIS LINE UNLESS YOU KNOW WHAT YOU'RE DOING #
###########################################################################

if [ ! `id -u` = 0 ]
then
    echo "E: $0 requires root privileges" > /dev/stderr
    exit 1
fi

if [ ! -d "frontend" ]
then
    echo "E: $0 should be run from the ConPaaS top-level directory" > /dev/stderr
    exit 1
fi

cd frontend 

CONPAAS_TARBALL="www/download/ConPaaS.tar.gz"

# Backup /var/www
if [ -d "/var/www" ]
then
    mv /var/www /var/backups/var_www-`date +%s`
fi

# Backup /etc/conpaas
if [ -d "/etc/conpaas" ]
then
    mv /etc/conpaas /var/backups/etc_conpaas-`date +%s`
fi

# Install the application under /var/www
cp -a www /var

# Put the configuration files under /etc/conpaas
cp -a conf /etc/conpaas

# Uncompress the ConPaaS release we want to work with
cp $CONPAAS_TARBALL . && tar xfz `basename $CONPAAS_TARBALL`

# Copy the necessary scripts
cp -a ConPaaS/config /etc/conpaas && rm -rf ConPaaS ConPaaS.tar.gz

# Fix permissions
chown -R www-data: /etc/conpaas /var/www

# Install the dependencies
apt-get update
apt-get -f -y install libapache2-mod-php5 php5-curl php5-mysql mysql-server mysql-client openssl unzip curl

# Get MySQL credentials
mysql_user=`awk '/^user/ { print $3 }' /etc/mysql/debian.cnf | head -n 1`
mysql_pass=`awk '/^password/ { print $3 }' /etc/mysql/debian.cnf | head -n 1`

# Change the DB config script
sed -i s/\'DB_USER\'/\'$mysql_user\'/ scripts/frontend-db.sql
sed -i s/\'DB_PASSWD\'/\'$mysql_pass\'/ scripts/frontend-db.sql

# Create ConPaaS database
mysql -u $mysql_user --password=$mysql_pass < scripts/frontend-db.sql

/bin/echo -e '[mysql]\nserver = "localhost"' > /etc/conpaas/db.ini
echo "user = \"$mysql_user\"" >> /etc/conpaas/db.ini
echo "pass = \"$mysql_pass\"" >> /etc/conpaas/db.ini
echo "db = \"DB_NAME\"" >> /etc/conpaas/db.ini

# Get and install the AWS SDK
wget http://pear.amazonwebservices.com/get/sdk-latest.zip
unzip sdk-latest.zip
cp -a sdk-*/* /var/www/lib/aws-sdk/
rm -rf sdk-*

cp /var/www/lib/aws-sdk/config-sample.inc.php /var/www/lib/aws-sdk/config.inc.php
sed -i s/"'key' => 'development-key',"/"'key' => '$EC2_USER', 'account_id' => '$EC2_ACCOUNT_ID',"/ /var/www/lib/aws-sdk/config.inc.php
sed -i s/"'secret' => 'development-secret',"/"'secret' => '$EC2_PASSWORD', 'canonical_id' => '$EC2_CANONICAL_ID',"/ /var/www/lib/aws-sdk/config.inc.php

# Hardcoded /etc/apache2/sites-available/default-ssl
cp conf/apache.conf.sample /etc/apache2/sites-available/default-ssl

# Create /var/www/config.php
cp /var/www/config-example.php /var/www/config.php

# reCAPTCHA config
sed -i s/'const CAPTCHA_PRIVATE_KEY.*'/"const CAPTCHA_PRIVATE_KEY = \'$CAPTCHA_PRIVATE_KEY\';"/ /var/www/config.php
sed -i s/'const CAPTCHA_PUBLIC_KEY.*'/"const CAPTCHA_PUBLIC_KEY = \'$CAPTCHA_PUBLIC_KEY\';"/ /var/www/config.php

# If we are installing the frontend on EC2 
if [ -f "/var/lib/ec2-bootstrap/user-data" ]
then
    # Then we know the public hostname
    hostname=`curl -s http://169.254.169.254/latest/meta-data/public-hostname`
    # Setting CONPAAS_HOST here to give a good default value to generate-certs.php
    sed -i s/'const CONPAAS_HOST.*'/"const CONPAAS_HOST = \'$hostname\';"/ /var/www/config.php
fi

# Generate SSL certificates and ask for hostname confirmation
php scripts/generate-certs.php /etc/conpaas/certs

# Get hostname
hostname=`openssl x509 -in /etc/conpaas/certs/cert.pem -text -noout|grep role=frontend | sed s/.*CN=//g | sed s#/.*##`
sed -i s/'const CONPAAS_HOST.*'/"const CONPAAS_HOST = \'$hostname\';"/ /var/www/config.php

# Enable SSL and restart apache
a2enmod ssl
a2ensite default-ssl
/etc/init.d/apache2 restart

# Edit conf/main.ini
sed -i s#^logfile.*#'logfile = "/var/log/conpaas-frontend.log"'# /etc/conpaas/main.ini

# Deploy on EC2
if [ -n "$AMI_ID" ]
then
    echo "ami = \"$AMI_ID\"" > /etc/conpaas/aws.ini
    echo "security_group = \"$SECURITY_GROUP\"" >> /etc/conpaas/aws.ini
    echo "keypair = \"$KEYPAIR\"" >> /etc/conpaas/aws.ini
    echo "instance_type = \"$EC2_INSTANCE_TYPE\"" >> /etc/conpaas/aws.ini

    /bin/echo -e "[iaas]\nDRIVER = EC2" > /etc/conpaas/config/cloud/ec2.cfg
    echo "USER = $EC2_USER" >> /etc/conpaas/config/cloud/ec2.cfg
    echo "PASSWORD = $EC2_PASSWORD" >> /etc/conpaas/config/cloud/ec2.cfg
    echo "IMAGE_ID = $AMI_ID" >> /etc/conpaas/config/cloud/ec2.cfg
    echo "SIZE_ID = $EC2_INSTANCE_TYPE" >> /etc/conpaas/config/cloud/ec2.cfg
    echo "SECURITY_GROUP_NAME = $SECURITY_GROUP" >> /etc/conpaas/config/cloud/ec2.cfg
    echo "KEY_NAME = $KEYPAIR" >> /etc/conpaas/config/cloud/ec2.cfg
# Deploy on OpenNebula
elif [ -n "$IMAGE" ]
then
    sed -i s#^enable_ec2.*#'enable_ec2 = "no"'# /etc/conpaas/main.ini
    sed -i s#^enable_opennebula.*#'enable_opennebula = "yes"'# /etc/conpaas/main.ini

    echo "instance_type = \"$ON_INSTANCE_TYPE\"" > /etc/conpaas/opennebula.ini
    echo "user = \"$ON_USER\"" >> /etc/conpaas/opennebula.ini
    echo "passwd = \"$ON_PASSWD\"" >> /etc/conpaas/opennebula.ini
    echo "image = \"$IMAGE\"" >> /etc/conpaas/opennebula.ini
    echo "network = \"$NETWORK\"" >> /etc/conpaas/opennebula.ini
    echo "url = \"$URL\"" >> /etc/conpaas/opennebula.ini
    echo "gateway = \"$GATEWAY\"" >> /etc/conpaas/opennebula.ini
    echo "nameserver = \"$NAMESERVER\"" >> /etc/conpaas/opennebula.ini

    /bin/echo -e "[iaas]\nDRIVER = OPENNEBULA" > /etc/conpaas/config/cloud/opennebula.cfg
    echo "USER = $ON_USER" >> /etc/conpaas/config/cloud/opennebula.cfg
    echo "PASSWORD = $ON_PASSWD" >> /etc/conpaas/config/cloud/opennebula.cfg
    echo "URL = $URL" >> /etc/conpaas/config/cloud/opennebula.cfg
    echo "IMAGE_ID = $IMAGE" >> /etc/conpaas/config/cloud/opennebula.cfg
    echo "NET_ID = $NETWORK" >> /etc/conpaas/config/cloud/opennebula.cfg
    echo "NET_GATEWAY = $GATEWAY" >> /etc/conpaas/config/cloud/opennebula.cfg
    echo "NET_NAMESERVER = $NAMESERVER" >> /etc/conpaas/config/cloud/opennebula.cfg
fi

echo "Installation completed!"
echo "Your ConPaaS system is online at the following URL: https://$hostname"