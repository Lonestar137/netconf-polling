#RUN AS root


#Setup service
echo 'Setting up systemd service'
sudo mv ./netc.service /etc/systemd/system/

#Timescale db install
echo 'Installing timescaledb. . . '
apt update
apt install gnupg postgresql-common
/usr/share/postgresql-common/pgdg/apt.postgresql.org.sh

sh -c "echo 'deb [signed-by=/usr/share/keyrings/timescale.keyring] https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"


wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | gpg --dearmor -o /usr/share/keyrings/timescale.keyring

apt update

#Note that it's version 12, may need to change the version to 14 or whatever you have.
apt install timescaledb-2-postgresql-12

exit
#Example Setup compression
psql -d grafana
#PSQL
CREATE TABLE if not exists cell_radio( timestamp TIMESTAMP, IP varchar(255), cellular_interface VARCHAR(255), radio_power_mode VARCHAR(255), technology VARCHAR(255), radio_rx_channel INT, radio_tx_channel INT, radio_band INT, bandwidth VARCHAR(255), radio_rssi INT, radio_rsrp INT, radio_rsrq INT, radio_snr FLOAT, radio_rat_preference VARCHAR(255), radio_rat_selected VARCHAR(255));
CREATE EXTENSION IF NOT EXISTS timescaledb;
SELECT create_hypertable('cell_radio', 'timestamp'); # + migrate_data => true  if not empty table.
ALTER TABLE cell_radio SET ( timescaledb.compress, timescaledb.compress_segmentby = 'ip' )
SELECT add_compression_policy('cell_radio', INTERVAL '2 hours')



#To see chunks for testing:
SELECT show_chunks('cell_radio', older_than => INTERVAL '3 days')
#Returns list of chunks 






echo'Restarting systemd and starting netc.service.'
sudo systemctl daemon-reload
sudo systemctl start netc.service

