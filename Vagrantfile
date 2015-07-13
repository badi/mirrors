# -*- mode: ruby -*-

machines = {
  :mirror => {:ip => "10.0.254.254",
              :box => "baremettle/ubuntu-14.04"},
  :test => {:ip => "10.0.254.253",
            :box => "baremettle/ubuntu-14.04"}
}

INVENTORY = 'inventory.txt'
HOSTS = 'hosts'

def inventory_line(name, ip, type="libvirt")
  "#{name} ansible_ssh_host=#{ip} ansible_ssh_private_key_file=.vagrant/machines/#{name}/#{type}/private_key\n"
end

def hosts_line(name, ip)
     "#{ip} #{name}\n"
end

def boot(config, box, name, ip)
  config.vm.define name do |node|
    node.vm.box = box
    node.vm.hostname = name
    node.vm.network :private_network, :ip => ip

    node.vm.provider :libvirt do |machine|
      machine.cpus = 1
      machine.memory = "1024"
    end

  end
end

File.open(INVENTORY, 'w').close()
File.open(HOSTS, 'w') do |fd|
  fd << "127.0.0.1 localhost" << "\n\n"
end

machines.each do |name, params|
  File.open(INVENTORY, 'a') do |fd|
    fd << inventory_line(name, params[:ip])
  end
  File.open(HOSTS, 'a') do |fd|
    fd << hosts_line(name, params[:ip])
  end
end

Vagrant.configure(2) do |config|

  machines.each do |name, params|
    boot config, params[:box], name, params[:ip]
  end

end
