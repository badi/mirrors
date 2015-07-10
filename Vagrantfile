# -*- mode: ruby -*-

File.open('inventory.txt', 'w') do |fd|
  fd << "10.0.254.254 ansible_ssh_private_key_file=.vagrant/machines/default/libvirt/private_key\n"
end

Vagrant.configure(2) do |config|
  config.vm.box = "baremettle/ubuntu-14.04"
  # config.vm.box_check_update = false

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  config.vm.network :private_network, :ip => "192.168.1.2",  :netmask => "255.255.0.0"
  config.vm.network :private_network, :ip => "10.0.254.254", :netmask => "255.255.0.0"

  config.vm.synced_folder ".", "/vagrant"

  config.vm.provider "libvirt" do |machine|
    machine.cpus = 1
    machine.memory = "1024"
  end

  config.vm.provision "shell", inline: <<-SHELL
    echo "deb http://repo.aptly.info/ squeeze main" >/etc/apt/sources.list.d/00-aptly.list
    apt-key adv --keyserver keys.gnupg.net --recv-keys E083A3782A194991
    apt-get update
    apt-get install -y bzip2 gnupg gpgv aptly
    gpg --no-default-keyring --keyring trustedkeys.gpg --keyserver keys.gnupg.net --recv-keys EC4926EA
    aptly mirror create ubuntu-cloud-trusty-kilo http://ubuntu-cloud.archive.canonical.com/ubuntu trusty-updates/kilo main
    aptly mirror update ubuntu-cloud-trusty-kilo
    aptly snapshot create ubuntu-cloud-trusty-kilo-$(date "+%F") from mirror ubuntu-cloud-trusty-kilo
    aptly publish snapshot ubuntu-cloud-trusty-kilo-$(date "+%F")
  SHELL

end
