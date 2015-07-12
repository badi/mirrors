# -*- mode: ruby -*-

File.open('inventory.txt', 'w') do |fd|
  fd << "10.0.254.254 ansible_ssh_private_key_file=.vagrant/machines/default/libvirt/private_key\n"
end

Vagrant.configure(2) do |config|
  config.vm.box = "baremettle/ubuntu-14.04"
  # config.vm.box_check_update = false

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  config.vm.network :private_network, :ip => "10.0.254.254", :netmask => "255.255.0.0"

  # config.vm.synced_folder ".", "/vagrant"

  config.vm.provider "libvirt" do |machine|
    machine.cpus = 1
    machine.memory = "1024"
  end

end
