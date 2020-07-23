# M-Bus based power meter Python exporter

## Hardware installation
This module was developed for and tested with the [inepro PRO380-MB power meter], hooked up to an [Elsaco SLC-33 M-Bus to serial] physical interface converter (part number `EI6033.02`).
The SLC-33 requires a serial port with 5V levels, therefore the [PremiumCord USB 2.0 -> RS-232] serial port adapter with the FTDI FT232R USB UART chip was used.

You can obviously use any M-Bus-to-serial and serial-to-USB adapter you want, these are just the confirmed working ones.

*Caution: only certified electrician can hook the PRO380-MB to the power grid. Always request the electrician to do this work for you. Working with live voltage can be live threatening!*
Follow the [PRO380 User Manual] to hook the meter up to the power grid. If your contract supports two tariffs, you can hook up the phase (via a circuit breaker) to tariff clamp 24 and a neutral (switched on by the power grid operator only in case the second tariff is active) to tariff clamp 25.

M-Bus/serial connection:
* The PRO380-MB clips 22 and 23 were connected to the SLC-33 clips 23 and 24 (M-Bus does not really mind the polarity; if there were more meters connected,.
* SLC-33
  * 12V power source was hooked up to SLC-33 pins 21 and 22 (mind the polarity!).
  * dip switches needed to be moved to the right position (RS-232 mode)
* Serial port connection:
 * serial port pin 2 (RXD) to SLC-33 pin 11 (Tx)
 * serial port pin 3 (TXD) to SLC-33 pin 12 (Rx)
 * serial port pin 5 (GND) to SLC-33 pin 13 (SG)

To ease the serial port connection, I have also bought a cheap serial-to-serial RS232 cable ([ROLINE RS232 Cable, DB9 M-F]) and only used the female connector + cable of it.

## Software installation
1. Create `/opt/power_meter` directory and clone this repo to it.
2. Install your distributional package with `mbus-serial-request-data` binary. On Debian, run `apt-get -y install libmbus1`
3. Install requirements for this tool. Run `pip3 install -m requirements.txt`
4. Create unique port symlink:
  1. Edit and deploy `10-usbports.rules` to `/etc/udev/rules.d/` to create the `/dev/ttymeterBus` symlink to the real serial device.
  2. Update your `initramfs`, e.g. by running `update-initramfs -k all -u`.
  3. Reboot for the symlink to get created.
5. Configure the exporter:
  1. Copy `prometheus-mbus-exporter.yml.example` to `prometheus-mbus-exporter.yml`
  2. Edit baud rate, meter ID, serial port name, metrics webserver TCP port, and location.
  3. The default baud rate is `2400`, default meter ID is zero (`0`); both can be changed via the meter user interface.
6. Configure `systemd`:
  1. Deploy `power_meter_prometheus_exporter.service` to `/etc/systemd/system/`
  2. Run `systemctl daemon-reload && systemctl enable power_meter_prometheus.service && systemctl start power_meter_prometheus.service`
7. Call `curl http://localhost:<port-number>/metrics` and observe the counters

## References
[inepro PRO380-MB power meter]: https://ineprometering.com/pro380/
[Elsaco SLC-33 M-Bus to serial]: http://www.elsaco.cz/index.php?file=./produkty/piggy/628_slc33.php
[PremiumCord USB 2.0 -> RS-232]: https://www.gmelectronic.com/converter-usb2-0-to-serial-port-com-premiumcord-ku2-232a
[ROLINE RS232 Cable, DB9 M-F]: https://www.secomp.co.uk/en_GB/roline-rs232-cable-db9-m-f-1-8-m/i/11016218
[PRO380 User Manual]: https://ineprometering.com/wp-content/uploads/2019/04/PRO380-user-manual-V2.18v6.pdf
