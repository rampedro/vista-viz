window.Vista = (function() {
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GeoJSON Viewer & Editor with Dynamic Insets and Data Mapping</title>

    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
    <link href="https://unpkg.com/tabulator-tables@5.6.1/dist/css/tabulator.min.css" rel="stylesheet" />

    <style>
        /* Reset & base */
        * {
            box-sizing: border-box;
        }
        body, html {
            margin: 0; padding: 0; height: 100%;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            flex-direction: column;
        }

        header, footer {
            background: #004466;
            color: white;
            padding: 10px 20px;
            text-align: center;
            user-select: none;
            flex-shrink: 0; /* Prevent header/footer from shrinking */
        }

        main {
            flex: 1;
            display: flex;
            height: calc(100vh - 96px); /* header + footer ~96px */
            min-height: 400px;
            overflow: hidden; /* Prevent main from overflowing */
        }

        #map {
            flex: 1 1 60%;
            min-width: 300px;
            height: 100%;
            position: relative;
            background: #e0e0e0; /* Placeholder background */
        }

        #sidebar {
            flex: 1 1 40%;
            display: flex;
            flex-direction: column;
            min-width: 320px;
            height: 100%;
            border-left: 1px solid #ddd;
            background: #f9f9f9;
        }

        #table {
            flex: 1;
            padding: 8px;
            overflow: auto; /* Allow table to scroll if content exceeds space */
        }

        #mappingControls {
            padding: 12px 16px;
            border-top: 1px solid #ddd;
            background: #fff;
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 8px 15px;
            align-items: center;
            flex-wrap: wrap; /* Allow controls to wrap */
            flex-shrink: 0; /* Prevent controls from shrinking */
        }

        #mappingControls label {
            font-weight: 600;
            white-space: nowrap; /* Prevent labels from wrapping */
        }

        #mappingControls select {
            padding: 4px 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            width: 100%; /* Make selects fill their grid cell */
        }

        #addPropertySection {
            padding: 12px 16px;
            border-top: 1px solid #ddd;
            background: #fff;
            display: flex;
            gap: 10px;
            flex-shrink: 0;
        }

        #addPropertySection input {
            flex: 1;
            padding: 6px 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }

        #addPropertySection button {
            padding: 6px 12px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        #addPropertySection button:hover {
            background-color: #0056b3;
        }

        /* Responsive stack on smaller screens */
        @media (max-width: 900px) {
            main {
                flex-direction: column;
                height: auto;
            }
            #map, #sidebar {
                flex: none;
                width: 100%;
                height: 50vh;
                min-height: 200px;
                border-left: none;
                border-top: 1px solid #ddd;
            }
            #sidebar {
                border-top: 1px solid #ddd;
            }
            #mappingControls {
                grid-template-columns: 1fr; /* Stack controls vertically */
            }
        }

        /* Inset map styling */
        #insetMap {
            position: absolute;
            bottom: 12px;
            right: 12px;
            width: 180px;
            height: 140px;
            border: 2px solid #004466;
            box-shadow: 0 0 8px rgba(0,0,0,0.3);
            z-index: 1000;
            background: white;
            border-radius: 6px;
            overflow: hidden; /* Hide excess map tiles */
        }

        /* Custom styles for map features */
        .leaflet-interactive.active-feature {
            stroke: #000 !important; /* !important to ensure override */
            stroke-width: 3 !important;
            fill-opacity: 0.8 !important;
        }

        /* Loading Spinner */
        #loadingSpinner {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 1001;
            font-size: 1.2em;
            color: #004466;
            background: rgba(255, 255, 255, 0.8);
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            display: none; /* Hidden by default */
        }
    </style>
</head>
<body>
<header>
    <h1>GeoJSON Viewer & Editor with Dynamic Insets and Data Mapping</h1>
</header>

<main>
    <div id="map">
        <div id="loadingSpinner">Loading data...</div>
        <div id="insetMap"></div>
    </div>
    <aside id="sidebar">
        <div id="table"></div>
        <div id="addPropertySection">
            <input type="text" id="newPropertyInput" placeholder="New Property Name (e.g., 'Density')" />
            <button onclick="addNewProperty()">Add Property</button>
        </div>
        <div id="mappingControls">
            <label for="fillColorPropertySelect">Fill Color By:</label>
            <select id="fillColorPropertySelect">
                <option value="none">-- None --</option>
            </select>

            <label for="strokeColorPropertySelect">Stroke Color By:</label>
            <select id="strokeColorPropertySelect">
                <option value="none">-- None --</option>
            </select>

            <label for="strokeWeightPropertySelect">Stroke Weight By:</label>
            <select id="strokeWeightPropertySelect">
                <option value="none">-- None --</option>
            </select>

            <label for="lineTypePropertySelect">Line Type By:</label>
            <select id="lineTypePropertySelect">
                <option value="none">-- None --</option>
                <option value="solid">Solid</option>
                <option value="dashed">Dashed</option>
                <option value="dotted">Dotted</option>
            </select>
        </div>
    </aside>
</main>

<footer>
    <small>Powered by Leaflet, Tabulator, and D3.js</small>
</footer>





    let geoData = {}; // Stores the raw GeoJSON data
    let mainMapGeojsonLayer; // Reference to the main map's GeoJSON layer
    let insetMapGeojsonLayer; // Reference to the inset map's GeoJSON layer
    let tabulatorTable; // Reference to the Tabulator table instance
    let selectedFeatureName = null; // To keep track of the currently selected feature by name
    let layerMap = {}; // name → Leaflet layer for main map features for quick access

    // State for current mapping selections
    let currentMapping = {
        fillColor: 'GDP', // Default mapping
        strokeColor: 'none',
        strokeWeight: 'Population', // Default mapping
        lineType: 'none'
    };

    // D3 color scale for quantitative data
    const quantColorScale = d3.scaleSequential(d3.interpolateYlOrRd).domain([0, 300]); // Example for GDP

    // D3 scale for stroke width
    const strokeWeightScale = d3.scaleLinear().range([1, 5]); // Domain will be set dynamically

    // Map instances
    const map = L.map('map').setView([55, -96], 4); // Centered on Canada
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    const insetMap = L.map('insetMap', {
        attributionControl: false,
        zoomControl: false,
        dragging: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
        tap: false,
        touchZoom: false,
    }).setView([55, -96], 2); // Centered on Canada with a lower zoom

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: ''
    }).addTo(insetMap);

    let viewRect = null; // Rectangle representing main map viewport on inset

    // --- Helper Functions ---

    // Shows/hides the loading spinner
    function showLoadingSpinner(show) {
        document.getElementById('loadingSpinner').style.display = show ? 'block' : 'none';
    }

    // Determines if a property is numeric
    function isNumericProperty(propertyName) {
        if (!geoData.features || geoData.features.length === 0) return false;
        // Check the first feature's property type
        const value = geoData.features.find(f => f.properties.hasOwnProperty(propertyName))?.properties[propertyName];
        return typeof value === 'number' || (typeof value === 'string' && !isNaN(parseFloat(value)));
    }

    // Gets all unique property keys from the GeoJSON features
    function getAllPropertyKeys() {
        let allKeys = new Set();
        geoData.features.forEach(f => {
            Object.keys(f.properties).forEach(key => allKeys.add(key));
        });
        return Array.from(allKeys).sort(); // Sorted for consistent dropdown order
    }

    // Function to update the domain of D3 scales based on the selected property
    function updateScaleDomains() {
        // Update color scale domain
        if (currentMapping.fillColor !== 'none') {
            const values = geoData.features.map(f => f.properties[currentMapping.fillColor]).filter(v => typeof v === 'number' || (!isNaN(parseFloat(v)) && v !== null && v !== ''));
            if (values.length > 0) {
                quantColorScale.domain(d3.extent(values.map(Number))); // Convert to number for domain calculation
            }
        }

        // Update stroke weight scale domain
        if (currentMapping.strokeWeight !== 'none') {
            const values = geoData.features.map(f => f.properties[currentMapping.strokeWeight]).filter(v => typeof v === 'number' || (!isNaN(parseFloat(v)) && v !== null && v !== ''));
            if (values.length > 0) {
                strokeWeightScale.domain(d3.extent(values.map(Number))); // Convert to number for domain calculation
            }
        }
    }

    // Function to style GeoJSON features based on current mapping and individual overrides
    function featureStyle(feature) {
        const props = feature.properties;
        const isSelected = selectedFeatureName === props.name;

        // Default styles
        let fillColor = '#3388ff'; // Default blue
        let strokeColor = '#555555'; // Default grey
        let strokeWeight = 1;
        let dashArray = null;
        let fillOpacity = 0.5;

        // Apply fill color mapping
        if (currentMapping.fillColor !== 'none' && (typeof props[currentMapping.fillColor] === 'number' || (!isNaN(parseFloat(props[currentMapping.fillColor])) && props[currentMapping.fillColor] !== null && props[currentMapping.fillColor] !== ''))) {
            fillColor = quantColorScale(Number(props[currentMapping.fillColor]));
        }

        // Apply stroke color mapping (simple example: could use scale for categorical)
        if (currentMapping.strokeColor !== 'none' && props[currentMapping.strokeColor] !== undefined) {
             // For now, if mapped, just set a consistent color or implement a categorical scale
            // You might extend this to use a d3.scaleOrdinal for categorical stroke colors
            strokeColor = 'black';
        }

        // Apply stroke weight mapping
        if (currentMapping.strokeWeight !== 'none' && (typeof props[currentMapping.strokeWeight] === 'number' || (!isNaN(parseFloat(props[currentMapping.strokeWeight])) && props[currentMapping.strokeWeight] !== null && props[currentMapping.strokeWeight] !== ''))) {
            strokeWeight = strokeWeightScale(Number(props[currentMapping.strokeWeight]));
        }

        // Apply line type mapping
        if (currentMapping.lineType !== 'none' && props[currentMapping.lineType] !== undefined) {
            const mappedLineType = String(props[currentMapping.lineType]).toLowerCase(); // Ensure string and lowercase
            if (mappedLineType === "dashed") dashArray = "8 8";
            else if (mappedLineType === "dotted") dashArray = "2 6";
            else dashArray = null; // Solid
        }

        // Apply highlight for selected feature
        if (isSelected) {
            strokeWeight = 3; // Thicker border for selected
            strokeColor = '#000'; // Black border for selected
            fillOpacity = 0.8;
        }

        return {
            fillColor: fillColor,
            color: strokeColor,
            weight: strokeWeight,
            dashArray: dashArray,
            fillOpacity: fillOpacity,
            className: isSelected ? 'active-feature' : ''
        };
    }

    // Updates the GeoJSON layer on the main map
    function updateMainMapGeoJSON() {
        if (mainMapGeojsonLayer) {
            map.removeLayer(mainMapGeojsonLayer);
        }

        updateScaleDomains(); // Recalculate D3 scale domains before styling

        mainMapGeojsonLayer = L.geoJSON(geoData, {
            style: featureStyle,
            onEachFeature: (feature, layer) => {
                const name = feature.properties.name;
                layerMap[name] = layer; // Store layer reference
                layer.bindPopup(`<b>${name}</b><pre>${JSON.stringify(feature.properties, null, 2)}</pre>`);
                layer.on('click', () => {
                    selectRegion(name);
                });
            }
        }).addTo(map);

        // Ensure the selected feature is brought to front after redrawing
        if (selectedFeatureName && layerMap[selectedFeatureName]) {
            layerMap[selectedFeatureName].bringToFront();
        }
    }

    // Updates the GeoJSON layer on the inset map
    function updateInsetGeoJSON() {
        if (insetMapGeojsonLayer) {
            insetMap.removeLayer(insetMapGeojsonLayer);
        }
        insetMapGeojsonLayer = L.geoJSON(geoData, {
            style: {
                color: '#666',
                weight: 1,
                fillOpacity: 0.1
            }
        }).addTo(insetMap);
    }

    // Updates the inset map's viewport rectangle
    function updateInsetViewRect() {
        const bounds = map.getBounds();

        if (viewRect) {
            insetMap.removeLayer(viewRect);
        }

        viewRect = L.rectangle(bounds, {
            color: "#ff7800",
            weight: 2,
            fillOpacity: 0,
            interactive: false
        }).addTo(insetMap);
    }

    // Populates the dropdowns for mapping properties
    function populateMappingSelects() {
        const propertyKeys = getAllPropertyKeys(); // Get all available properties

        const fillSelect = document.getElementById('fillColorPropertySelect');
        const strokeSelect = document.getElementById('strokeColorPropertySelect');
        const weightSelect = document.getElementById('strokeWeightPropertySelect');
        const lineTypeSelect = document.getElementById('lineTypePropertySelect'); // Add line type select

        // Store current selected values to re-select after clearing
        const currentFill = fillSelect.value;
        const currentStroke = strokeSelect.value;
        const currentWeight = weightSelect.value;
        const currentLineType = lineTypeSelect.value;

        // Clear existing options, but keep "None" and static line types
        [fillSelect, strokeSelect, weightSelect].forEach(select => {
            select.innerHTML = '<option value="none">-- None --</option>';
        });
        // lineTypeSelect has static options, just ensure the "none" option
        if (!lineTypeSelect.querySelector('option[value="none"]')) {
            lineTypeSelect.insertAdjacentHTML('afterbegin', '<option value="none">-- None --</option>');
        }

        // Add properties to selects based on their type
        propertyKeys.forEach(key => {
            const isNum = isNumericProperty(key);
            const optionText = key.replace(/([A-Z])/g, ' $1').trim(); // Make readable

            // Fill Color: prefers numeric, but can accept any for future categorical mapping
            let fillOption = document.createElement('option');
            fillOption.value = key;
            fillOption.textContent = optionText;
            fillSelect.appendChild(fillOption);

            // Stroke Color: prefers numeric or categorical
            let strokeOption = document.createElement('option');
            strokeOption.value = key;
            strokeOption.textContent = optionText;
            strokeSelect.appendChild(strokeOption);

            // Stroke Weight: only numeric
            if (isNum) {
                let weightOption = document.createElement('option');
                weightOption.value = key;
                weightOption.textContent = optionText;
                weightSelect.appendChild(weightOption);
            }

            // Line Type: for string properties that might contain 'solid', 'dashed', 'dotted'
            // For now, we'll just add all properties and let the `featureStyle` handle validation
            // An advanced version might inspect actual values before adding.
            let lineTypeOption = document.createElement('option');
            lineTypeOption.value = key;
            lineTypeOption.textContent = optionText;
            lineTypeSelect.appendChild(lineTypeOption);
        });

        // Re-set previous selections, or default to 'none' if property no longer exists
        fillSelect.value = currentFill && propertyKeys.includes(currentFill) ? currentFill : 'none';
        strokeSelect.value = currentStroke && propertyKeys.includes(currentStroke) ? currentStroke : 'none';
        weightSelect.value = currentWeight && propertyKeys.includes(currentWeight) && isNumericProperty(currentWeight) ? currentWeight : 'none';
        lineTypeSelect.value = currentLineType && propertyKeys.includes(currentLineType) ? currentLineType : 'none';

        // Update current mapping state to reflect the actual selected values
        currentMapping.fillColor = fillSelect.value;
        currentMapping.strokeColor = strokeSelect.value;
        currentMapping.strokeWeight = weightSelect.value;
        currentMapping.lineType = lineTypeSelect.value;
    }


    // Initialize Tabulator table
    function initializeTabulator() {
        const tableData = geoData.features.map((f, idx) => ({
            _tabulator_id: idx, // Tabulator uses 'id' for internal tracking, avoid conflict with GeoJSON 'id'
            ...f.properties
        }));

        const columns = getAllPropertyKeys().map(k => ({
            title: k.replace(/([A-Z])/g, ' $1').trim(), // Format column headers nicely
            field: k,
            editor: "input",
            sorter: isNumericProperty(k) ? "number" : "string", // Smart sort
            headerFilter: "input", // Add header filter for searching
            hozAlign: isNumericProperty(k) ? "right" : "left", // Align numeric columns to right
            formatter: (cell) => { // Format numbers to locale string
                const value = cell.getValue();
                // Ensure value is numeric for formatting, otherwise return as is
                return typeof value === 'number' && !isNaN(value) ? value.toLocaleString() : value;
            }
        }));

        tabulatorTable = new Tabulator("#table", {
            data: tableData,
            layout: "fitColumns",
            movableColumns: true,
            resizableColumns: true,
            selectable: 1, // Allow only one row to be selected at a time
            columns: columns,
            // Changed cellEdited to dataChanged for broader update scope
            dataEdited: onDataEdited, // Called when any data in the table is changed
            rowClick: onRowClick,
            dataLoaded: function(data){
                // Ensure table selects row if map already has a selected feature
                if (selectedFeatureName) {
                    const row = this.getRows().find(r => r.getData().name === selectedFeatureName);
                    if (row) row.select();
                }
            }
        });
    }

    // New handler for any data change in Tabulator
    function onDataEdited(data) {
        // Find the specific feature in geoData that was edited
        const editedFeature = geoData.features.find(f => f.properties.name === data[0].name); // data is an array of edited rows
        if (!editedFeature) return;

        // Update the geoData properties from the edited row data
        Object.assign(editedFeature.properties, data[0]);

        // Re-apply style for just the edited feature to show immediate visual change
        if (layerMap[editedFeature.properties.name]) {
            const layer = layerMap[editedFeature.properties.name];
            layer.setStyle(featureStyle(editedFeature));
            layer.getPopup().setContent(`<b>${editedFeature.properties.name}</b><pre>${JSON.stringify(editedFeature.properties, null, 2)}</pre>`);
        }

        // Check if any of the edited properties are currently mapped.
        // If so, a global map update is needed because D3 scales' domains might have changed.
        const editedFields = Object.keys(data[0]).filter(key => key !== '_tabulator_id'); // Get only actual data fields
        const needsGlobalUpdate = editedFields.some(field =>
            field === currentMapping.fillColor ||
            field === currentMapping.strokeWeight ||
            field === currentMapping.strokeColor ||
            field === currentMapping.lineType
        );

        if (needsGlobalUpdate) {
            // A global update will re-evaluate all styles and update scales
            updateMainMapGeoJSON();
        }
    }


    // On table row click, select the corresponding map region
    function onRowClick(e, row) {
        const name = row.getData().name;
        selectRegion(name);
    }

    // Selects a region on the map and table
    function selectRegion(name) {
        selectedFeatureName = name;

        // Update table selection
        if (tabulatorTable) {
            tabulatorTable.deselectRow();
            const row = tabulatorTable.getRows().find(r => r.getData().name === name);
            if (row) {
                row.select();
                tabulatorTable.scrollToRow(row, "center", false);
            }
        }

        // Update map highlight (re-apply styles for all to clear previous and set new)
        mainMapGeojsonLayer.eachLayer(layer => {
            layer.setStyle(featureStyle(layer.feature));
        });

        if (layerMap[name]) {
            layerMap[name].bringToFront(); // Bring selected layer to top
        }
    }

    // Adds a new property column to the data and table
    function addNewProperty() {
        const newPropName = document.getElementById('newPropertyInput').value.trim();
        if (!newPropName) {
            alert("Please enter a name for the new property.");
            return;
        }
        // Check if property name is valid (e.g., doesn't contain spaces or special chars for object keys)
        if (!/^[a-zA-Z0-9_]+$/.test(newPropName)) {
            alert("Property names should only contain letters, numbers, and underscores.");
            return;
        }

        if (getAllPropertyKeys().includes(newPropName)) {
            alert(`Property '${newPropName}' already exists.`);
            return;
        }

        // Add new property to all features with a default empty value
        geoData.features.forEach(f => {
            f.properties[newPropName] = ""; // Default to empty string
        });

        // Re-initialize Tabulator to add the new column
        initializeTabulator();
        populateMappingSelects(); // Update mapping dropdowns with new property
        document.getElementById('newPropertyInput').value = ''; // Clear input
        updateMainMapGeoJSON(); // Re-render map in case a mapping was set
    }


    // --- Event Listeners ---

    // Map events for inset map
    map.on('move', updateInsetViewRect);
    map.on('zoom', updateInsetViewRect);
    insetMap.on('click', (e) => {
        map.panTo(e.latlng);
    });

    // Mapping control change listeners
    document.getElementById('fillColorPropertySelect').addEventListener('change', (e) => {
        currentMapping.fillColor = e.target.value;
        updateMainMapGeoJSON();
    });
    document.getElementById('strokeColorPropertySelect').addEventListener('change', (e) => {
        currentMapping.strokeColor = e.target.value;
        updateMainMapGeoJSON();
    });
    document.getElementById('strokeWeightPropertySelect').addEventListener('change', (e) => {
        currentMapping.strokeWeight = e.target.value;
        updateMainMapGeoJSON();
    });
    document.getElementById('lineTypePropertySelect').addEventListener('change', (e) => {
        currentMapping.lineType = e.target.value;
        updateMainMapGeoJSON();
    });


    // --- Initialization ---

    showLoadingSpinner(true);
    fetch("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/canada.geojson")
        .then(res => res.json())
        .then(json => {
            geoData = json;
            // Add random Population and GDP for demonstration
            geoData.features.forEach(f => {
                f.properties.Population = Math.floor(Math.random() * 5_000_000 + 500_000);
                f.properties.GDP = +(Math.random() * 300 + 20).toFixed(1);
                f.properties.UnemploymentRate = +(Math.random() * 10 + 2).toFixed(1); // New numeric property
                // Ensure a lineType property exists for demo purposes, if not already present
                if (!f.properties.lineType) {
                    const lineTypes = ["solid", "dashed", "dotted"];
                    f.properties.lineType = lineTypes[Math.floor(Math.random() * lineTypes.length)];
                }
            });

            // Initial setup after data is loaded
            populateMappingSelects(); // Populate dropdowns before map rendering
            updateMainMapGeoJSON();
            updateInsetGeoJSON();
            updateInsetViewRect();
            initializeTabulator();
            showLoadingSpinner(false);
        })
        .catch(error => {
            console.error("Error loading GeoJSON data:", error);
            showLoadingSpinner(false);
            document.getElementById('loadingSpinner').textContent = 'Error loading data. See console.';
        });



</body>
</html>

 return this; 
}).call({});