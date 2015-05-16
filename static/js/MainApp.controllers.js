var controllers = angular.module('MainApp.controllers', []);

controllers.controller('MainController', ['$scope', '$http', '$routeParams', 'TaskData', 'AuctionService', function ($scope, $http, $routeParams, TaskData, AuctionService) {
	$scope.isCollapsed = true;
	$scope.filterEnabled = false;
	$scope.isLoading = false;

	$scope.$on("$routeChangeStart", function(event, next, current) {
		$scope.isAuction = (next.controller == "AuctionController")
	});

	$scope.refresh = function() {
		AuctionService.refresh();
	};
	/*
		$http.get("/refresh").success(function(data) {
			TaskData.register(data.task_id, function(result) {
				if (result.status == 'SUCCESS') {
					console.log('Refresh task success');
					
					
				}
				console.log("res: ");
				console.log(result);
			});
			//
		});
	*/

	$scope.refreshAuction = function(auction_name) {
		var name = (typeof auction_name !== 'undefined') ? auction_name : $routeParams.name
		$http.get("/auction/" + name + "/refresh").success(function (data) {
			TaskData.register(data.task_id, function(task_data) {
				console.log(task_data);
			});
		});
	}
}]);

controllers.controller('ListController', ['$scope', 'AuctionService', 'Auction', function ($scope, AuctionService, Auction) {
	$scope.auctions = function() {
		return AuctionService.auctions();
	}
}]);

controllers.controller('AuctionController', ['$scope', '$routeParams', 'Auction', 'Item', '$http', 'itemFactory',  function ($scope, $routeParams, Auction, Item, $http, itemFactory) {
	$scope.auctionId = $routeParams.name;
	$scope.auctions = Auction.get({name: $routeParams.name});
	$scope.back = function() { window.history.back() };
	$scope.currentPage = 0;
	$scope.pageSize = 20;
	$scope.numberOfPages = $scope.auctions.items / $scope.pageSize;
	$scope.items = []
	
	$scope.fetch = function() {
		$http.get("/auction/" + $routeParams.name + "/list", { params: { 'page': $scope.currentPage } }).success(function(data, status) {
			$scope.items = $scope.items.concat(data);
		});
	};

	$scope.loadNext = function() {
		$scope.currentPage = $scope.currentPage+1;
		$scope.fetch();
	};

	$scope.followToggle = function(item) {
		$scope.items = itemFactory.updateItems($scope.items, itemFactory.followToggle(item));
	}

	$scope.refresh = function() {
	console.log('debug me')
		$scope.refreshAuction($routeParams.name);	
	}

	$scope.fetch();
}]);

controllers.controller('FollowController', ['$scope', '$http', 'itemFactory', function($scope, $http, itemFactory) {
	$scope.update = function() {
		// update, and group by auction
		$http.get('/auction').success(function(auctions, status) {

			$http.get('/followed').success(function(followed, status) {
				
				followedAuctions = [];

				for (var i = 0; i < auctions.length; i++) {
					auctions[i].items = [];
					for (var j = 0; j < followed.length; j++) {
						if (followed[j].auction_name == auctions[i].name) {
							// check if we're 'using' this auction
							if(followedAuctions.indexOf(auctions[i]) == -1) {
								followedAuctions.push(auctions[i]);
							}
							followedAuctions[followedAuctions.indexOf(auctions[i])].items.push(followed[j]);
						}
					}
				}
				$scope.followed = followedAuctions;
			});
		});
	};

	// refresh item on backend
	$scope.refresh = function(item) {
		$http.get("/auction/"+ item.auction_name +"/" + item.item_id + "/refresh").success(function(followed, status) {
			$scope.update();
		});
	}

	$scope.followToggle = function(item) {
		item = itemFactory.followToggle(item);
	}

	$scope.update();
}]);

controllers.controller('BidController', ['$scope', '$http', function($scope, $http) {
	$scope.data = {
		auction_name: $scope.item.auction_name,
		item_id: $scope.item.item_id,
		bidder_number: "",
		bidder_password: "",
		max_bid: $scope.item.next_price
	};
	$scope.submitBid = function() {
		$http.post('/bid', JSON.stringify($scope.data)).success(function(data, status) {

		});
		console.log($scope.item);
	}
}]);

