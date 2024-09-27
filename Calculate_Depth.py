import os
from paraview.simple import *
import numpy as np

# Specify the patch to use for viewing depth (e.g., bottom)
patch_name = 'patch/bottom'  # You can change this as needed

# Set the mode for running the script
use_current_directory = False  # Set to False to use specified case locations and compare cases, or set to True to just look at current working directory

if use_current_directory:
    # Use the current working directory
    dir = os.path.dirname(os.path.abspath(__file__))  # Absolute path of the script file
    filename = os.path.join(dir, 'case.foam')
    cases_to_resample = [filename]
else:
    # Specify case locations
    base_case_location = r'C:\Users\RDCHLDDB\Documents\Ubend0.2\Ubend0.2'  # Folder containing the base case
    cases_to_resample = [
        r'C:\Users\RDCHLDDB\Documents\Ubend0.2\Ubend0.2\case.foam',
        r'C:\Users\RDCHLDDB\Documents\Ubend0.2\Ubend0.2_2\case.foam',
        # Add more cases as needed
    ]

# Load the base case
casefoam = OpenFOAMReader(registrationName='base_case', FileName=os.path.join(base_case_location, 'case.foam'))
casefoam.UpdatePipeline()
casefoam.MeshRegions = [patch_name]  # Set the bottom patch for the first dataset

# Initialize a list to hold depth calculators for appending later
depth_calculators = []

# Function to set normal array to None
def set_normal_array_to_none(display):
    display.SelectNormalArray = 'None'

# Function to set global lighting options
def set_global_lighting_options():
    render_view = GetActiveViewOrCreate('RenderView')
    render_view.UseLight = 0  # Disable the default lighting
    render_view.OrientationAxesVisibility = 0  # Optionally hide orientation axes
    render_view.Background = [1.0, 1.0, 1.0]  # Set background to white, change as needed

# Set global lighting options
set_global_lighting_options()

# Iterate over each case to resample
for case in cases_to_resample:
    # Extract the base folder name from the case path
    base_folder_name = os.path.basename(os.path.dirname(case))

    # Load the second dataset with alpha.water
    casefoam_1 = OpenFOAMReader(registrationName=f'{base_folder_name}_case.foam_1', FileName=case)
    casefoam_1.CellArrays = ['alpha.water']
    casefoam_1.UpdatePipeline()

    # Create a contour on the second dataset for alpha.water at 0.5
    contour1 = Contour(registrationName=f'{base_folder_name}_Contour1', Input=casefoam_1)
    contour1.ContourBy = ['POINTS', 'alpha.water']
    contour1.Isosurfaces = [0.5]
    contour1.PointMergeMethod = 'Uniform Binning'
    contour1.UpdatePipeline()  # Update the contour filter

    # Create a new calculator to calculate elevation (WSE) from the contour and name it WSE
    calculator1 = Calculator(registrationName=f'{base_folder_name}_Calculator1', Input=contour1)
    calculator1.Function = 'coordsZ'  # Calculate the Z-coordinate as elevation
    calculator1.ResultArrayName = 'WSE'  # Rename the result to WSE
    calculator1.UpdatePipeline()  # Update the calculator filter

    # Convert the calculator output (applied to contour) to a point cloud
    convertToPointCloud1 = ConvertToPointCloud(registrationName=f'{base_folder_name}_ConvertToPointCloud1', Input=calculator1)
    convertToPointCloud1.UpdatePipeline()  # Update the point cloud filter

    # Get bounds of casefoam_1
    bounds = casefoam_1.GetDataInformation().GetBounds()
    xmin, xmax, ymin, ymax, zmin, zmax = bounds

    # Calculate the origin and scale for the PointVolumeInterpolator
    origin = [xmin, ymin, zmin]
    scale = [1.1 * (xmax - xmin), 1.1 * (ymax - ymin), 1.1 * (zmax - zmin)]

    # Use PointVolumeInterpolator with defined 'Bounded Volume'
    pointVolumeInterpolator2 = PointVolumeInterpolator(
        registrationName=f'{base_folder_name}_PointVolumeInterpolator2',
        Input=convertToPointCloud1,
        Source='Bounded Volume'
    )

    # Set the origin and scale for the bounded volume
    pointVolumeInterpolator2.Source.Origin = origin
    pointVolumeInterpolator2.Source.Scale = scale
    pointVolumeInterpolator2.UpdatePipeline()  # Update the interpolator filter

    # Resample With Dataset onto the base case for the first iteration
    resampleWithDataset1 = ResampleWithDataset(
        registrationName=f'{base_folder_name}_ResampleWithDataset1',
        SourceDataArrays=pointVolumeInterpolator2,
        DestinationMesh=casefoam if base_folder_name == 'Ubend0.2' else depth_calculator
    )
    resampleWithDataset1.CellLocator = 'Static Cell Locator'  # Set cell locator
    resampleWithDataset1.UpdatePipeline()  # Ensure the resampling filter is updated

    # Create a display for the resampled dataset
    resampleWithDataset1Display = Show(resampleWithDataset1, GetActiveViewOrCreate('RenderView'))
    set_normal_array_to_none(resampleWithDataset1Display)  # Set normal array to None

    # Create a new calculator to compute Depth
    depthCalculator = Calculator(registrationName=f'Depth_{base_folder_name}', Input=resampleWithDataset1)
    depthCalculator.Function = 'WSE - coordsZ'  # Subtract WSE from coordsZ to calculate Depth
    depthCalculator.ResultArrayName = f'Depth_{base_folder_name}'  # Name the result 'Depth' with base folder name

    depthCalculator.UpdatePipeline()  # Update the calculator filter

    # Ensure the display settings are applied to depthCalculator
    depthCalculatorDisplay = Show(depthCalculator, GetActiveViewOrCreate('RenderView'))
    set_normal_array_to_none(depthCalculatorDisplay)  # Set normal array to None

    # Append the current depth calculator to the list for later
    depth_calculators.append(depthCalculator)  # Add the depth calculator to the list

# Create a new 'Append Attributes' to combine depth calculations
if depth_calculators:
    appendAttributes2 = AppendAttributes(registrationName='AppendAttributes2', Input=depth_calculators)
    appendAttributes2.UpdatePipeline()  # Update the append filter

    # Show the appended attributes
    appendAttributesDisplay = Show(appendAttributes2, GetActiveViewOrCreate('RenderView'))
    set_normal_array_to_none(appendAttributesDisplay)  # Set normal array to None

# Final application of all components
