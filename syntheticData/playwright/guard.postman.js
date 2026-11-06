pm.test('Guarded simulation backend responds', function () {
  pm.response.to.have.status(200);
});
pm.test('Simulation collection is selected', function () {
  pm.expect(pm.response.json().collection).to.eql('simulation');
});
