var controllers = angular.module('MainApp.controllers', []);

controllers.controller('MainController', ['$scope', '$http', '$routeParams', 'TaskData', 'AuctionService', 'Loading', function ($scope, $http, $routeParams, TaskData, AuctionService, Loading) {
	$scope.isCollapsed = true;
	$scope.filterEnabled = false;

	$scope.isLoading = function() {
		return Loading.isLoading();
	};

	$scope.$on("$routeChangeStart", function(event, next, current) {
		$scope.isAuction = (next.controller == "AuctionController")
	});

	$scope.refresh = function() {
		AuctionService.refreshList();
	};

	$scope.refreshAuction = function() {
		var name = (typeof auction_name !== 'undefined') ? auction_name : $routeParams.name
		AuctionService.refreshAuction(name);	
	};
}]);

controllers.controller('ListController', ['$scope', 'AuctionService', function ($scope, AuctionService) {
	$scope.auctions = function() {
		return AuctionService.auctionList();
	}
}]);

controllers.controller('AuctionController', ['$scope', '$routeParams', 'AuctionService', 'Item', '$http', 'itemFactory',  function ($scope, $routeParams, AuctionService, Item, $http, itemFactory) {

	$scope.auctionId = $routeParams.name;
	$scope.back = function() { window.history.back() };
	$scope.currentPage = 0;
	$scope.pageSize = 20;
	AuctionService.auction($routeParams.name, function(auction) {
		$scope.numberOfPages = auction.items / $scope.pageSize;
	});

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
		AuctionService.refreshAuction($routeParams.name);
		//$scope.refreshAuction($routeParams.name);	
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

