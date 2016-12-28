#!/bin/bash
set -e

main()
{
  echo '[i] Setting up'
  mkdir -p /var/log/cronup
  touch /var/log/cronup.log
  which python
}

main