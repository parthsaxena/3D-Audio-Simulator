var sheet = new GraphPaper.Sheet(
    document.getElementById('sheet'),   // DOM element of the Sheet
    window                              // parent window 
);
var source_id = 0;
var new_entity_mode = false;
var lastEntity = null;
var audioSources = [];

sheet.on(GraphPaper.SheetEvent.CLICK, (eventData) => {
    const id = 'source' + source_id;
    var divEntity = document.createElement("div");
    divEntity.setAttribute("id", id);
    divEntity.setAttribute("class", "source_entity");
    var divTranslateHandle = document.createElement("div");
    divTranslateHandle.setAttribute("id", "translateHandle" + source_id);
    divEntity.appendChild(divTranslateHandle);
    var divConnectorAnchor = document.createElement("div");
    divConnectorAnchor.setAttribute("id", "connectorAnchor" + source_id);
    divEntity.appendChild(divConnectorAnchor);
    document.getElementById("sheet").insertBefore(divEntity, document.getElementById("sheet").firstChild);

    if (!lastEntity || !new_entity_mode) {
        document.getElementById('audioFileInput').click();
        document.getElementById('audioFileInput').onchange = (e) => {
            const file = e.target.files[0];
            const reader = new FileReader();
            reader.onload = (e) => {
                const audioData = e.target.result;
                addEntity(eventData, divEntity, divTranslateHandle, divConnectorAnchor, audioData);
            };
            reader.readAsDataURL(file);
        };
    } else {
        addEntity(eventData, divEntity, divTranslateHandle, divConnectorAnchor);
    }
});

function addEntity(eventData, divEntity, divTranslateHandle, divConnectorAnchor, audioData = null) {
    const entity = new GraphPaper.Entity(
        divEntity.id,
        eventData.targetPoint.getX(),
        eventData.targetPoint.getY(),
        40,
        40,
        sheet,
        divEntity,
        [divTranslateHandle],
        []
    );
    sheet.addEntity(entity);

    if (new_entity_mode && lastEntity !== null) {
        // continuing an existing path
        const anchorLast = lastEntity.addInteractableConnectorAnchor(document.getElementById('connectorAnchor' + (source_id - 1)));
        anchorLast.setPossibleRoutingPointDirections(["top", "left", "bottom", "right"]);
        const anchorCurrent = entity.addInteractableConnectorAnchor(divConnectorAnchor);
        anchorCurrent.setPossibleRoutingPointDirections(["top", "left", "bottom", "right"]);
        sheet.makeNewConnectorFromAnchors(anchorLast, anchorCurrent);
        console.log('Connecting entities ' + anchorLast + " and " + anchorCurrent);
        
        // add to existing path
        audioSources[audioSources.length - 1].path.push({
            x: eventData.targetPoint.getX(),
            y: eventData.targetPoint.getY(),
            entity: entity,
            id: divEntity.id
        });
    } else {
        // starting a new path or point source
        audioSources.push({
            path: [{
                x: eventData.targetPoint.getX(),
                y: eventData.targetPoint.getY(),
                entity: entity
            }],
            audioData: audioData,
            id: divEntity.id
        });
        lastEntity = entity;
    }
    
    lastEntity = new_entity_mode ? entity : null;
    source_id++;
}

sheet = sheet.scale(0.5, true)
sheet.setGrid(new GraphPaper.Grid(40.0, '#424242', GraphPaper.GRID_STYLE.LINE))

const entity = new GraphPaper.Entity(
    'user',                                    // id
    500,                                                  // x        
    500,                                                  // y
    40,                                                 // width
    40,                                                 // height
    sheet,                                              // parent GraphPaper.Sheet
    document.getElementById('entity1'),                 // DOM element for the entity
    [document.getElementById('translateHandle')],       // DOM elements for the object's translation handles
    []                                                  // DOM elements for the object's resize handles
);
sheet.addEntity(entity);

sheet.initTransformationHandlers();
sheet.initInteractionHandlers();
sheet.initConnectorRoutingWorker();
sheet.setConnectorRefreshBufferTime(0);

document.getElementById('modeToggle').addEventListener('change', function() {
    new_entity_mode = this.checked;
    if (!new_entity_mode) {
        lastEntity = null;
    }
});

document.getElementById('simulateButton').addEventListener('click', function() {
    var audioData = JSON.stringify({ audioSources: window.audioSources });
    fetch('/simulate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: audioData
    })
    .then(response => response.json())
    .then(data => {
        if (data.audioData) {            
            var audioPlayer = document.createElement('audio');
            audioPlayer.controls = true;
            var sourceElement = document.createElement('source');
            sourceElement.src = data.audioData;
            sourceElement.type = 'audio/wav';  
            
            audioPlayer.appendChild(sourceElement);
            var playerContainer = document.getElementById('audioPlayerContainer');
            playerContainer.innerHTML = '';
            playerContainer.appendChild(audioPlayer);
            audioPlayer.load();
            
            audioPlayer.play().catch(e => console.error('Error during playback:', e));
        }
        // document.getElementById('responseArea').innerText = JSON.stringify(data, null, 2);
    })
    .catch(error => console.error('Error:', error));
});




