#!/bin/bash
if [ "x$1" = "x" ]; then
    exit
fi
export PATH=''
exec /bin/bash --noprofile --norc -r << EOF

source $1

print_var()
{
    if [ ! "x\$2" = "x" ]; then
        echo -e "\$1 = '\${2//\'/\\\\\'}'"
    else
        echo "\$1 = None"
    fi
}

print_int()
{
    if [ ! "x\$2" = "x" ]; then
        echo -e "\$1 = \$2"
    else
        echo "\$1 = None"
    fi
}

print_array()
{
    key=\$1; shift
    if [ ! "x\$1" = "x" ]; then
        array=( "\$@" )
        echo -n "\$key = ["
        for i in \${array[@]}; do echo -n "'\$i',"; done
        echo "]"
    else
        echo "\$key = []"
    fi
}

print_var   name        "\$pkgname"
print_var   version     "\$pkgver"
print_int   release     "\$pkgrel"
print_var   description "\$pkgdesc"
print_var   url         "\$url"
print_array licenses    "\${license[@]}"
print_array groups      "\${groups[@]}"
print_array arch        "\${arch[@]}"
print_array depends     "\${depends[@]}"
print_array makedepends "\${makedepends[@]}"
print_array provides    "\${provides[@]}"
print_array conflicts   "\${conflicts[@]}"
print_array replaces    "\${replaces[@]}"
print_array install     "\${install[@]}"
print_array source      "\${source[@]}"
print_array md5sums     "\${md5sums[@]}"
print_array sha1sums    "\${sha1sums[@]}"
print_array sha256sums  "\${sha256sums[@]}"
print_array sha384sums  "\${sha384sums[@]}"
print_array sha512sums  "\${sha512sums[@]}"
EOF
