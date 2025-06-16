from DashAI.back.types.inf.ptype.PtypeCat import PtypeCat
from DashAI.back.types.inf.ptype.Machines import Machines, MACHINES
import DashAI.back.types.inf.ptype.Machine as Machine
from pathlib import Path
import joblib


#This class could heir from PtypeCat, but it would require change the scaler and the LR model.
class DashAIPtype(PtypeCat):
    """
    
    A class to represent a DashAI Ptype inference method.
    This class extends the InferenceMethod and PtypeCat classes to provide
    functionality for inferring types in DashAI applications.
    
    """

    def __init__(self):
        
        self.types = [
            "integer",
            "string",
            "float",
            "boolean",
            "date-iso-8601",
            "date-eu",
            "date-non-std-subtype",
            "date-non-std",
        ]

        #In case of wanting to add a new type:
        #Create the machine in ptype/Machine.py file
        #Add the new machine to the current_machines dictionary.
        #Add the new type to this list.
        self.types.extend([
            "time",
        ])
        
        current_machines = {
            **MACHINES, 
            "time": Machine.Time()
        } 

        self.machines = Machines(self.types, current_machines)
        self.verbose = False
        self.lr_clf = joblib.load(Path(__file__).parent / "ptype" / "LR.sav")
        self.scaler = joblib.load(Path(__file__).parent / "ptype" / "scaler.pkl")

    
    
        
