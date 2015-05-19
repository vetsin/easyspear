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
services.factory("Loading", [function() {
	var count = 0;
	return {
		add: function() {
			count++;
		},
		complete: function() {
			count--;
		},
		isLoading: function() {
			return (count != 0)
		},
	}
}]);
/* Service for real-time updates */
services.factory("AuctionService", ['Auction', 'TaskData', '$http', function(Auction, TaskData, $http) {
	// private
	var auctionList = Auction.query();
	// public
	return {
		auctionList: function() {
			//auctions = Auction.query();
			return auctionList;
		},
		auction: function(auction_name, cb) {
			return Auction.get({name:auction_name}, cb);
		},
		refreshList: function() {
			$http.get("/refresh").success(function(data) {
				TaskData.register(data.task_id, function(result) {
					if (result.status == 'SUCCESS') {
						console.log('Server auction listing refreshed');
						auctionList = Auction.query();
					}
				});
			});
		},
		refreshAuction: function(auction_name, cb) {
			$http.get("/auction/" + auction_name + "/refresh").success(function (data) {
				TaskData.register(data.task_id, function(task_data) {
					if (result.status == 'SUCCESS') {
						console.log('Updated auction: ' + auction_name);
						// just update the list again
						auctionList = Auction.query(); 
						// then the auction...
						return Auction.get({name:auction_name}, cb);
					}
				});
			});
		},
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
