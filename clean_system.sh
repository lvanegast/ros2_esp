#!/bin/bash
set -e

echo "==> 1. Limpiando caché de paquetes APT..."
apt clean

echo "==> 2. Eliminando revisiones antiguas y deshabilitadas de Snap..."
snap list --all | awk '/disabled/{print $1, $3}' | while read name rev; do
    echo "Eliminando $name (revisión $rev)..."
    snap remove "$name" --revision="$rev" 2>/dev/null || true
done

echo "==> 3. Estado de espacio en disco:"
df -h /

echo "==> ¡Limpieza del sistema completada con éxito!"
