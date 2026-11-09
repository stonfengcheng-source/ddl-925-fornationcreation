"""Verify and boot a separately extracted v7 archive, without a browser."""
import runpy
import create_product_v6
import create_product_v7

create_product_v6.DEST = create_product_v7.package.DEST
create_product_v6.REQUIRED = create_product_v7.package.REQUIRED
runpy.run_path(str(create_product_v6.ROOT / "scripts/verify_product_v6.py"), run_name="__main__")
