# Clean shared shell profile. No history or accounts from the build device.
[[ $- != *i* ]] && return
export TMPDIR=/tmp
export EDITOR=nano
PS1="[\u@\h \W]\$ "
