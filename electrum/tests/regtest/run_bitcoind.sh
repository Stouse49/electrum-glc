#!/usr/bin/env bash
export HOME=~
set -eux pipefail
mkdir -p ~/.goldcoin
cat > ~/.goldcoin/goldcoin.conf <<EOF
regtest=1
txindex=1
printtoconsole=1
rpcuser=doggman
rpcpassword=donkey
rpcallowip=127.0.0.1
zmqpubrawblock=tcp://127.0.0.1:28332
zmqpubrawtx=tcp://127.0.0.1:28333
fallbackfee=0.0002
[regtest]
rpcbind=0.0.0.0
rpcport=18554
EOF
rm -rf ~/.goldcoin/regtest
bitcoind -regtest &
sleep 6
goldcoin-cli createwallet test_wallet
addr=$(goldcoin-cli getnewaddress)
goldcoin-cli generatetoaddress 150 $addr
tail -f ~/.goldcoin/regtest/debug.log
