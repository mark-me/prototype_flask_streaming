// Zet CSV data om naar JSON voor Tabulator
const csvData = {{ data| tojson }};

// Maak kolommen dynamisch aan op basis van het eerste rijtje
const columns = csvData.length > 0 ? csvData[0].map((_, i) => ({
    title: `Kolom ${i + 1}`,
    field: `col${i}`,
    editor: "input"
})) : [];

// Zet csvData om naar objecten voor Tabulator
const tableData = csvData.map(row => {
    let obj = {};
    row.forEach((cell, i) => {
        obj[`col${i}`] = cell;
    });
    return obj;
});

// Maak Tabulator tabel
const table = new Tabulator("#csv-table", {
    data: tableData,
    layout: "fitColumns",
    columns: columns,
    cellEdited: function (cell) {
        // Optioneel: iets doen na edit
    },
});

function submitCSV() {
    const data = table.getData();
    // Zet terug om naar CSV string
    let csvRows = data.map(row => {
        return Object.values(row).map(v => v.toString().replace(/,/g, '')).join(",");
    });
    document.getElementById('csv_data').value = csvRows.join("\n");
    return true; // formulier versturen
}