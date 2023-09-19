document.addEventListener('DOMContentLoaded', function () {
    const filterSelect = document.getElementById('filter-select');
    const filterForm = document.getElementById('filter-form');

    function submitFormOnAllSelected() {
        if (filterSelect.value === 'all') {
            filterForm.submit();
        }
    }

    filterSelect.addEventListener('change', function () {
        filterForm.submit();
    });

});
