var services = angular.module('MainApp.services', ['ngResource']);

services.factory("Auction", ['$resource', '$http', 
	function($resource, $http) {
		return $resource('auction/:name', {name:'@name'}, {
			"list": {url:'auction/:name/list', isArray: true}
		});
	}
]);
services.factory("Item", ['$resource',
	function($resource) {
		return $resource('auction/:name/:id', {name:'@name',id:'@id'}, {
		});
	}
]);
/* Service for real-time updates */
services.factory("TaskService", ['$rootScope', '$http', function($rootScope, $http) {
	return {
		checkTask: function(task_id) {
			$http.get('/tasks/' + task_id).success(function (data) {
				//
			});
		}
	}
}]);

/* Service for displaying 'happened x seconds ago' */
services.factory("NotificationService", ['$rootScope', function($rootScope) {
	// events:
	var TIME_AGO_TICK = "e:timeAgo";
	var timeAgoTick = function() {
		$rootScope.$broadcast(TIME_AGO_TICK);
	}
	// every minute, publish/$broadcast a TIME_AGO_TICK event
	setInterval(function() {
		timeAgoTick();
		$rootScope.$apply();
	}, 1000 * 60);
	return {
		//pub
		timeAgoTick: timeAgoTick,
		//sub
		onTimeAgo: function($scope, element, attrs, handler) {
			$scope.$on(TIME_AGO_TICK, function() {
				//$scope.timeStr = handler(attrs);
				handler(element, attrs);
			});
		}
	}
}]);
