"""Execute the entire notebook in a new kernel using this Python environment."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

root=Path(__file__).resolve().parent
if "--download" in sys.argv:
    from analysis import download_inputs
    download_inputs()
notebooks=list(root.glob("*.ipynb"))
assert len(notebooks)==1
with tempfile.TemporaryDirectory(prefix="portfolio-notebook-") as temp:
    kernel=Path(temp)/"kernels"/"python3"
    kernel.mkdir(parents=True)
    (kernel/"kernel.json").write_text(json.dumps({"argv":[sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"],
                                               "display_name":"Python 3","language":"python"}))
    os.environ.setdefault("MPLCONFIGDIR",str(Path(temp)/"matplotlib"))
    specs=KernelSpecManager(kernel_dirs=[str(kernel.parent)])
    km=KernelManager(kernel_name="python3",kernel_spec_manager=specs)
    nb=nbformat.read(notebooks[0],as_version=4)
    # Remove every prior result so successful execution cannot reuse saved state.
    for cell in nb.cells:
        if cell.cell_type=="code": cell.outputs=[];cell.execution_count=None
    client=NotebookClient(nb,km=km,timeout=600,resources={"metadata":{"path":str(root)}})
    try:
        client.execute(cwd=str(root))
    finally:
        if km.has_kernel:
            km.shutdown_kernel(now=True)
    cells=[c for c in nb.cells if c.cell_type=="code"]
    assert all(c.execution_count is not None for c in cells)
    assert not any(o.output_type=="error" for c in cells for o in c.outputs)
    nbformat.write(nb,notebooks[0])
    result=json.loads((root/"validation.json").read_text())
    result["clean_notebook_run"]={"executed_code_cells":len(cells),"error_outputs":0,
       "embedded_figures":sum("image/png" in o.get("data",{}) for c in cells for o in c.outputs),
       "notebook_sha256":hashlib.sha256(notebooks[0].read_bytes()).hexdigest(),
       "analysis_sha256":hashlib.sha256((root/"analysis.py").read_bytes()).hexdigest()}
    result["status"]="clean_kernel_verified"
    (root/"validation.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(result["clean_notebook_run"])
