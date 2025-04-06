// postman: GET /todos 테스트
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});
pm.test("Response should be an array", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.be.an('array');
});
